from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from api.engine import analyse
from api.providers import MarketProvider, MacroProvider
from api.intelligence import intelligence_snapshot, fetch_news, fetch_cot_gold
from api.market_activity import activity_snapshot, oil_snapshot, shipping_snapshot
from api.equity_data import equity_snapshot
from api.luna import ask_luna

app = FastAPI(title="NIGHT Quant Terminal API", version="0.7.1")
market = MarketProvider()
macro = MacroProvider()

class Credentials(BaseModel):
    twelve_key: str | None = None
    fred_key: str | None = None
    gemini_key: str | None = None
    openrouter_key: str | None = None
    oanda_token: str | None = None
    oanda_account: str | None = None

class AnalysisRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "5m"
    credentials: Credentials | None = None

class LiveBarsRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "5m"
    bars: list[dict]
    credentials: Credentials | None = None
    source: str = "browser realtime stream"
    volume_type: str = "tick volume"

class ChatRequest(BaseModel):
    message: str
    analysis: dict
    credentials: Credentials | None = None

class EquityRequest(BaseModel):
    symbol: str
    credentials: Credentials | None = None

class LunaRequest(BaseModel):
    message: str
    context: dict | None = None
    credentials: Credentials | None = None

def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

def _event_risk_from_news(news: dict) -> float:
    keywords=["federal reserve","fed chair","pce","cpi","payroll","nfp","war","attack","tariff","hormuz","sanction","rate decision","shipping","tanker","red sea"]
    hits=0
    for a in (news.get("articles") or [])[:18]:
        t=(a.get("title") or "").lower();hits+=sum(1 for k in keywords if k in t)
    return min(86.0,18.0+hits*4.0)

@app.get("/api/health")
def health():return {"status":"ok","service":"night-quant-terminal","version":"0.7.1"}

async def _institutional_context(symbol: str, creds: dict):
    macro_data=await macro.snapshot(symbol,creds)
    intel=intelligence_snapshot(symbol);news=intel.get("news",{});cot=intel.get("cot",{});activity=activity_snapshot()
    base_macro=float(macro_data.get("macro_score",0.0));base_inter=float(macro_data.get("intermarket_score",0.0));news_score=float(news.get("score",0.0));cot_score=float(cot.get("score",0.0)) if symbol.upper()=="XAUUSD" else 0.0
    if symbol.upper()=="XAUUSD":
        macro_data["macro_score"]=_clamp(.65*base_macro+.20*news_score+.15*cot_score);macro_data["intermarket_score"]=_clamp(.85*base_inter+.15*news_score)
    else:macro_data["macro_score"]=_clamp(.80*base_macro+.20*news_score)
    event_risk=_event_risk_from_news(news)
    return macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score

async def _decorate_result(symbol,result,macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score):
    result["macro_source"]=macro_data.get("macro_source");result["macro_details"]=macro_data.get("macro_details",{});result["news"]=news;result["cot"]=cot;result["activity"]=activity;result["event_risk"]=event_risk
    result["institutional_factors"]={"fred_macro":round(base_macro,4),"fred_intermarket":round(base_inter,4),"gdelt_news":round(news_score,4),"cftc_cot":round(cot_score,4),"blended_macro":round(float(macro_data.get("macro_score",0.0)),4)}
    return result

async def _analyse_one(symbol,timeframe,creds):
    market_data=await market.snapshot(symbol,timeframe,creds)
    macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score=await _institutional_context(symbol,creds)
    result=analyse(symbol,timeframe,{**market_data,"macro":macro_data,"event_risk":event_risk});result["provider_errors"]=market_data.get("provider_errors",[])
    return await _decorate_result(symbol,result,macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score)

@app.post("/api/analyse")
async def run_analysis(req:AnalysisRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};return await _analyse_one(req.symbol,req.timeframe,creds)

@app.post("/api/bars")
async def get_seed_bars(req:AnalysisRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};data=await market.snapshot(req.symbol,req.timeframe,creds)
    return {"symbol":req.symbol.upper(),"timeframe":req.timeframe,"bars":data.get("bars",[]),"source":data.get("source","none"),"volume_type":data.get("volume_type","none"),"provider_errors":data.get("provider_errors",[])}

@app.post("/api/analyse-bars")
async def analyse_live_bars(req:LiveBarsRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score=await _institutional_context(req.symbol,creds)
    result=analyse(req.symbol,req.timeframe,{"bars":req.bars[-240:],"source":req.source,"volume_type":req.volume_type,"macro":macro_data,"event_risk":event_risk});result["stream_realtime"]=True
    return await _decorate_result(req.symbol,result,macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score)

@app.post("/api/analyse-mtf")
async def run_mtf(req:AnalysisRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};frames=["1m","5m","15m","1h","4h","1D"]
    results={tf:await _analyse_one(req.symbol,tf,creds) for tf in frames};valid=[v for v in results.values() if v.get("valid")]
    if not valid:return {"symbol":req.symbol.upper(),"valid":False,"timeframes":results}
    readiness=[v.get("trade_readiness",0.0) for v in valid];w={"1m":.06,"5m":.10,"15m":.14,"1h":.22,"4h":.26,"1D":.22}
    num=sum(results[tf].get("probability_up",50.0)*w[tf] for tf in frames if results[tf].get("valid"));den=sum(w[tf] for tf in frames if results[tf].get("valid")) or 1.0;p_up=num/den
    agreement=sum(1 for v in valid if (v.get("probability_up",50)>=55)==(p_up>=55))/len(valid);action="LONG" if p_up>=58 and agreement>=.60 else "SHORT" if p_up<=42 and agreement>=.60 else "WAIT"
    return {"symbol":req.symbol.upper(),"valid":True,"action":action,"probability_up":round(p_up,2),"probability_down":round(100-p_up,2),"agreement":round(agreement*100,2),"average_readiness":round(sum(readiness)/len(readiness),2),"timeframes":results}

@app.post("/api/equity")
def equity(req:EquityRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};return equity_snapshot(req.symbol,creds.get("twelve_key"))

@app.post("/api/luna")
def luna(req:LunaRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};return ask_luna(req.message,req.context or {},creds)

@app.get("/api/news/{symbol}")
def live_news(symbol:str):return fetch_news(symbol)
@app.get("/api/cot/gold")
def cot_gold():return fetch_cot_gold()
@app.get("/api/activity")
def live_activity():return activity_snapshot()
@app.get("/api/oil")
def live_oil():return oil_snapshot()
@app.get("/api/shipping")
def live_shipping():return shipping_snapshot()

@app.post("/api/chat")
def quant_chat(req:ChatRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};return ask_luna(req.message,req.analysis or {},creds)

@app.get("/api/calendar")
async def calendar():return {"events":await macro.calendar()}
@app.get("/api/modules")
def modules():return {"modules":["Realtime Browser Tick Stream","Realtime Tick Candle Builder","Live OHLCV Adapter","Equity Market Data","SEC EDGAR Fundamentals","Twelve Data Global Fundamentals","Exact MTF Quant","Volume/Flow","Regime","Probability/EV","FRED Macro","GDELT News Intelligence","CFTC COT Positioning","WTI/Brent/NatGas","Live AIS Shipping","Trade Readiness","Luna AI","Report Engine"]}
