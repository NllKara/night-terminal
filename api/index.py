from __future__ import annotations

import math
from fastapi import FastAPI
from pydantic import BaseModel
from api.engine import analyse
from api.providers import MarketProvider, MacroProvider
from api.intelligence import intelligence_snapshot, fetch_news, fetch_event_news, fetch_cot_gold
from api.event_prediction import predict_event, event_catalog
from api.market_activity import activity_snapshot, oil_snapshot, shipping_snapshot, shipping_exposure
from api.equity_data import equity_snapshot, equity_bars, search_equities
from api.luna import ask_luna

app=FastAPI(title="NIGHT Quant Terminal API",version="0.9.1");market=MarketProvider();macro=MacroProvider()
class Credentials(BaseModel):
    twelve_key:str|None=None;fred_key:str|None=None;gemini_key:str|None=None;openrouter_key:str|None=None;oanda_token:str|None=None;oanda_account:str|None=None
class AnalysisRequest(BaseModel):
    symbol:str="XAUUSD";timeframe:str="5m";credentials:Credentials|None=None
class LiveBarsRequest(BaseModel):
    symbol:str="XAUUSD";timeframe:str="5m";bars:list[dict];credentials:Credentials|None=None;source:str="browser realtime stream";volume_type:str="tick volume"
class ChatRequest(BaseModel):
    message:str;analysis:dict;credentials:Credentials|None=None
class EquityRequest(BaseModel):
    symbol:str;market:str|None=None;credentials:Credentials|None=None
class LunaRequest(BaseModel):
    message:str;context:dict|None=None;credentials:Credentials|None=None
class EventPredictionRequest(BaseModel):
    event:str="NFP";credentials:Credentials|None=None

def _clamp(x:float,lo:float=-1.0,hi:float=1.0)->float:return max(lo,min(hi,x))
def _squash(x:float,scale:float=2.0)->float:return math.tanh(float(x)/scale)
def _event_risk_from_news(news:dict)->float:
    keys=["federal reserve","fed chair","pce","cpi","payroll","nfp","employment","unemployment","wages","war","attack","tariff","hormuz","sanction","rate decision","shipping","tanker","red sea"];hits=0
    for a in (news.get("articles") or [])[:18]:
        t=(a.get("title") or "").lower();hits+=sum(1 for k in keys if k in t)
    return min(86.0,18.0+hits*4.0)

def _usd_sensitivity(symbol:str)->float:
    s=symbol.upper().replace("/","")
    if s in {"XAUUSD","XAGUSD"}:return -1.0
    if len(s)==6 and s.isalpha():
        if s.startswith("USD"):return 1.0
        if s.endswith("USD"):return -1.0
    return 0.0

def _usd_fundamental_from_macro(macro_data:dict)->float:
    d=macro_data.get("macro_details") or {}
    # USD direction: higher 2Y/real/10Y yields and firmer inflation support USD;
    # rising unemployment weakens USD. All inputs are standardized changes.
    z2=float(d.get("DGS2_change_z",0.0) or 0.0);zr=float(d.get("DFII10_change_z",0.0) or 0.0);z10=float(d.get("DGS10_change_z",0.0) or 0.0);zu=float(d.get("UNRATE_change_z",0.0) or 0.0);zc=float(d.get("CPI_yoy_change_z",0.0) or 0.0)
    return _clamp(.32*_squash(z2)+.25*_squash(zr)+.13*_squash(z10)-.16*_squash(zu)+.14*_squash(zc))

async def _dxy_context(creds:dict)->dict:
    # DXY is a confirmation/common-factor layer. If the configured feeds cannot
    # supply DXY, NIGHT returns NO DATA rather than inventing a proxy price.
    try:
        md=await market.snapshot("DXY","1h",creds);bars=md.get("bars") or []
        if len(bars)<30:return {"available":False,"score":0.0,"probability_up":50.0,"source":md.get("source","none"),"provider_errors":md.get("provider_errors",[])}
        q=analyse("DXY","1h",{"bars":bars,"source":md.get("source","DXY feed"),"volume_type":md.get("volume_type","unknown"),"macro":{"macro_score":0.0,"intermarket_score":0.0,"freshness":md.get("freshness",1.0)},"event_risk":15.0})
        edge=float(q.get("edge",0.0) or 0.0)
        return {"available":True,"score":_clamp(edge*2.0),"probability_up":float(q.get("probability_up",50.0)),"action":q.get("action"),"regime":q.get("regime"),"source":md.get("source"),"last_price":q.get("last_price")}
    except Exception as e:return {"available":False,"score":0.0,"probability_up":50.0,"source":"none","error":type(e).__name__}

@app.get("/api/health")
def health():return {"status":"ok","service":"night-quant-terminal","version":"0.9.1"}

async def _institutional_context(symbol:str,creds:dict):
    macro_data=await macro.snapshot(symbol,creds);intel=intelligence_snapshot(symbol);news=intel.get("news",{});cot=intel.get("cot",{});activity=activity_snapshot();dxy=await _dxy_context(creds)
    base_macro=float(macro_data.get("macro_score",0.0));base_inter=float(macro_data.get("intermarket_score",0.0));news_score=float(news.get("score",0.0));cot_score=float(cot.get("score",0.0)) if symbol.upper()=="XAUUSD" else 0.0
    usd_fund=_usd_fundamental_from_macro(macro_data);usd_sens=_usd_sensitivity(symbol);dxy_score=float(dxy.get("score",0.0) or 0.0)
    # Common USD factor: fundamentals lead, DXY confirms, live USD-related news adds context.
    usd_common=_clamp(.60*usd_fund+.25*dxy_score+.15*news_score)
    if symbol.upper()=="XAUUSD":
        pair_macro=_clamp(.48*base_macro+.34*(usd_sens*usd_common)+.10*news_score+.08*cot_score)
        pair_inter=_clamp(.60*base_inter+.40*(usd_sens*dxy_score))
    elif usd_sens!=0:
        pair_macro=_clamp(.38*base_macro+.47*(usd_sens*usd_common)+.15*news_score)
        pair_inter=_clamp(.60*base_inter+.40*(usd_sens*dxy_score))
    else:
        pair_macro=_clamp(.80*base_macro+.20*news_score);pair_inter=base_inter
    macro_data["macro_score"]=pair_macro;macro_data["intermarket_score"]=pair_inter
    macro_data.setdefault("macro_details",{}).update({"usd_fundamental_score":round(usd_fund,4),"dxy_confirmation_score":round(dxy_score,4),"usd_common_factor":round(usd_common,4),"usd_pair_sensitivity":usd_sens})
    event_risk=_event_risk_from_news(news);return macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score,dxy,usd_fund,usd_common,usd_sens

async def _decorate_result(symbol,result,macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score,dxy,usd_fund,usd_common,usd_sens):
    result["macro_source"]=macro_data.get("macro_source");result["macro_details"]=macro_data.get("macro_details",{});result["news"]=news;result["cot"]=cot;result["activity"]=activity;result["event_risk"]=event_risk;result["dxy_analysis"]=dxy
    result["institutional_factors"]={"fred_pair_macro_raw":round(base_macro,4),"fred_intermarket_raw":round(base_inter,4),"usd_fundamental":round(usd_fund,4),"dxy_confirmation":round(float(dxy.get("score",0.0) or 0.0),4),"usd_common_factor":round(usd_common,4),"usd_pair_sensitivity":usd_sens,"gdelt_news":round(news_score,4),"cftc_cot":round(cot_score,4),"blended_macro":round(float(macro_data.get("macro_score",0.0)),4),"blended_intermarket":round(float(macro_data.get("intermarket_score",0.0)),4)}
    return result

async def _analyse_one(symbol,timeframe,creds):
    market_data=await market.snapshot(symbol,timeframe,creds);ctx=await _institutional_context(symbol,creds);macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score,dxy,usd_fund,usd_common,usd_sens=ctx;result=analyse(symbol,timeframe,{**market_data,"macro":macro_data,"event_risk":event_risk});result["provider_errors"]=market_data.get("provider_errors",[]);return await _decorate_result(symbol,result,macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score,dxy,usd_fund,usd_common,usd_sens)

@app.post("/api/analyse")
async def run_analysis(req:AnalysisRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};return await _analyse_one(req.symbol,req.timeframe,creds)
@app.post("/api/bars")
async def get_seed_bars(req:AnalysisRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};data=await market.snapshot(req.symbol,req.timeframe,creds);return {"symbol":req.symbol.upper(),"timeframe":req.timeframe,"bars":data.get("bars",[]),"source":data.get("source","none"),"volume_type":data.get("volume_type","none"),"provider_errors":data.get("provider_errors",[])}
@app.post("/api/analyse-bars")
async def analyse_live_bars(req:LiveBarsRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};ctx=await _institutional_context(req.symbol,creds);macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score,dxy,usd_fund,usd_common,usd_sens=ctx;result=analyse(req.symbol,req.timeframe,{"bars":req.bars[-240:],"source":req.source,"volume_type":req.volume_type,"macro":macro_data,"event_risk":event_risk});result["stream_realtime"]=True;return await _decorate_result(req.symbol,result,macro_data,news,cot,activity,event_risk,base_macro,base_inter,news_score,cot_score,dxy,usd_fund,usd_common,usd_sens)
@app.post("/api/analyse-mtf")
async def run_mtf(req:AnalysisRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};frames=["1m","5m","15m","1h","4h","1D"];results={tf:await _analyse_one(req.symbol,tf,creds) for tf in frames};valid=[v for v in results.values() if v.get("valid")]
    if not valid:return {"symbol":req.symbol.upper(),"valid":False,"timeframes":results}
    w={"1m":.06,"5m":.10,"15m":.14,"1h":.22,"4h":.26,"1D":.22};den=sum(w[tf] for tf in frames if results[tf].get("valid")) or 1;p_up=sum(results[tf].get("probability_up",50)*w[tf] for tf in frames if results[tf].get("valid"))/den;agreement=sum(1 for v in valid if (v.get("probability_up",50)>=55)==(p_up>=55))/len(valid);action="LONG" if p_up>=58 and agreement>=.60 else "SHORT" if p_up<=42 and agreement>=.60 else "WAIT";sample=valid[-1]
    return {"symbol":req.symbol.upper(),"valid":True,"action":action,"probability_up":round(p_up,2),"probability_down":round(100-p_up,2),"agreement":round(agreement*100,2),"average_readiness":round(sum(v.get("trade_readiness",0) for v in valid)/len(valid),2),"dxy_analysis":sample.get("dxy_analysis"),"institutional_factors":sample.get("institutional_factors"),"macro_details":sample.get("macro_details"),"timeframes":results}

@app.get("/api/equity/search")
def equity_search(q:str,limit:int=40):return {"query":q,"results":search_equities(q,max(1,min(limit,60)))}
@app.post("/api/equity")
def equity(req:EquityRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};snap=equity_snapshot(req.symbol,creds.get("twelve_key"),req.market);bars=snap.get("bars",[]);sig=analyse(req.symbol,"5m",{"bars":bars,"source":snap.get("price_source","equity feed"),"volume_type":"exchange/provider volume","freshness":1.0 if "LIVE" in snap.get("freshness","") else .75,"macro":{"macro_score":0.0,"intermarket_score":0.0,"freshness":.7},"event_risk":20.0})
    profile=((snap.get("fundamentals") or {}).get("profile") or {});ship=shipping_snapshot(350);snap["signal"]={"action":sig.get("action"),"bias":sig.get("bias"),"probability_up":sig.get("probability_up"),"probability_down":sig.get("probability_down"),"confidence":sig.get("confidence"),"readiness":sig.get("trade_readiness"),"regime":sig.get("regime")};snap["shipping_exposure"]=shipping_exposure(req.symbol,profile,ship);return snap
@app.post("/api/equity-mtf")
def equity_mtf(req:EquityRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};frames=["1m","5m","15m","1h","4h","1D"];out={}
    for tf in frames:
        d=equity_bars(req.symbol,creds.get("twelve_key"),tf,180,req.market);r=analyse(req.symbol,tf,{"bars":d.get("bars",[]),"source":d.get("source","none"),"volume_type":"exchange/provider volume","freshness":1.0 if "LIVE" in d.get("freshness","") else .75,"macro":{"macro_score":0.0,"intermarket_score":0.0,"freshness":.7},"event_risk":20.0});out[tf]={**r,"freshness":d.get("freshness"),"source":d.get("source")}
    valid=[v for v in out.values() if v.get("valid")]
    if not valid:return {"symbol":req.symbol.upper(),"valid":False,"timeframes":out}
    w={"1m":.06,"5m":.10,"15m":.14,"1h":.22,"4h":.26,"1D":.22};p=sum(out[tf].get("probability_up",50)*w[tf] for tf in frames if out[tf].get("valid"))/(sum(w[tf] for tf in frames if out[tf].get("valid")) or 1);agree=sum(1 for v in valid if (v.get("probability_up",50)>=55)==(p>=55))/len(valid);act="LONG" if p>=58 and agree>=.60 else "SHORT" if p<=42 and agree>=.60 else "WAIT";return {"symbol":req.symbol.upper(),"valid":True,"action":act,"probability_up":round(p,2),"probability_down":round(100-p,2),"agreement":round(agree*100,2),"timeframes":out}

@app.post("/api/luna")
def luna(req:LunaRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};return ask_luna(req.message,req.context or {},creds)
@app.get("/api/news/{symbol}")
def live_news(symbol:str):return fetch_news(symbol)
@app.get("/api/news-event")
def live_event_news(event:str="NFP",limit:int=30):return fetch_event_news(event,max(5,min(limit,50)))
@app.get("/api/news-prediction/events")
def prediction_events():return {"events":event_catalog()}
@app.post("/api/news-prediction")
def pre_release_prediction(req:EventPredictionRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};return predict_event(req.event,creds)
@app.get("/api/cot/gold")
def cot_gold():return fetch_cot_gold()
@app.get("/api/activity")
def live_activity():return activity_snapshot()
@app.get("/api/oil")
def live_oil():return oil_snapshot()
@app.get("/api/shipping")
def live_shipping(limit:int=700):return shipping_snapshot(max(50,min(limit,1200)))
@app.get("/api/shipping/exposure/{symbol}")
def live_shipping_exposure(symbol:str):return shipping_exposure(symbol,{},shipping_snapshot(350))
@app.post("/api/chat")
def quant_chat(req:ChatRequest):
    creds=req.credentials.model_dump(exclude_none=True) if req.credentials else {};return ask_luna(req.message,req.analysis or {},creds)
@app.get("/api/calendar")
async def calendar():return {"events":await macro.calendar()}
@app.get("/api/modules")
def modules():return {"modules":["Searchable US/IDX Equity Universe","Realtime/Latest Equity Market Data","Equity Signals","Equity MTF Direction","Stock Shipping Exposure","Global AIS Shipping Analytics","SEC EDGAR Fundamentals","Twelve Data Global Fundamentals","Exact MTF Quant","Volume/Flow","Regime","Probability/EV","FRED Macro","USD Fundamental Common Factor","DXY Confirmation For FX Pairs","Live News with GDELT + Google News fallback","Pre-release Macro Event Prediction","CFTC COT Positioning","WTI/Brent/NatGas","Trade Readiness","Luna AI via OpenRouter","Report Engine"]}
