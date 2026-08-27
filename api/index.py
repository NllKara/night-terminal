from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from api.engine import analyse
from api.providers import MarketProvider, MacroProvider
from api.intelligence import intelligence_snapshot, fetch_news, fetch_cot_gold
from api.market_activity import activity_snapshot, oil_snapshot, shipping_snapshot

app = FastAPI(title="NIGHT Quant Terminal API", version="0.5.0")
market = MarketProvider()
macro = MacroProvider()


class Credentials(BaseModel):
    twelve_key: str | None = None
    oanda_token: str | None = None
    oanda_account: str | None = None
    fred_key: str | None = None


class AnalysisRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "5m"
    credentials: Credentials | None = None


class ChatRequest(BaseModel):
    message: str
    analysis: dict


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _event_risk_from_news(news: dict) -> float:
    keywords = ["federal reserve", "fed chair", "pce", "cpi", "payroll", "nfp", "war", "attack", "tariff", "hormuz", "sanction", "rate decision", "shipping", "tanker", "red sea"]
    hits = 0
    for a in (news.get("articles") or [])[:18]:
        t = (a.get("title") or "").lower()
        hits += sum(1 for k in keywords if k in t)
    return min(86.0, 18.0 + hits * 4.0)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "night-quant-terminal", "version": "0.5.0"}


async def _analyse_one(symbol: str, timeframe: str, creds: dict):
    market_data = await market.snapshot(symbol, timeframe, creds)
    macro_data = await macro.snapshot(symbol, creds)
    intel = intelligence_snapshot(symbol)
    news = intel.get("news", {})
    cot = intel.get("cot", {})
    activity = activity_snapshot()

    base_macro = float(macro_data.get("macro_score", 0.0))
    base_inter = float(macro_data.get("intermarket_score", 0.0))
    news_score = float(news.get("score", 0.0))
    cot_score = float(cot.get("score", 0.0)) if symbol.upper() == "XAUUSD" else 0.0

    if symbol.upper() == "XAUUSD":
        macro_data["macro_score"] = _clamp(0.65 * base_macro + 0.20 * news_score + 0.15 * cot_score)
        macro_data["intermarket_score"] = _clamp(0.85 * base_inter + 0.15 * news_score)
    else:
        macro_data["macro_score"] = _clamp(0.80 * base_macro + 0.20 * news_score)

    event_risk = _event_risk_from_news(news)
    payload = {**market_data, "macro": macro_data, "event_risk": event_risk}
    result = analyse(symbol, timeframe, payload)
    result["provider_errors"] = market_data.get("provider_errors", [])
    result["macro_source"] = macro_data.get("macro_source")
    result["macro_details"] = macro_data.get("macro_details", {})
    result["news"] = news
    result["cot"] = cot
    result["activity"] = activity
    result["event_risk"] = event_risk
    result["institutional_factors"] = {
        "fred_macro": round(base_macro, 4),
        "fred_intermarket": round(base_inter, 4),
        "gdelt_news": round(news_score, 4),
        "cftc_cot": round(cot_score, 4),
        "blended_macro": round(float(macro_data.get("macro_score", 0.0)), 4),
    }
    return result


@app.post("/api/analyse")
async def run_analysis(req: AnalysisRequest):
    creds = req.credentials.model_dump(exclude_none=True) if req.credentials else {}
    return await _analyse_one(req.symbol, req.timeframe, creds)


@app.post("/api/analyse-mtf")
async def run_mtf(req: AnalysisRequest):
    creds = req.credentials.model_dump(exclude_none=True) if req.credentials else {}
    frames = ["1m", "5m", "15m", "1h", "4h", "1D"]
    results = {tf: await _analyse_one(req.symbol, tf, creds) for tf in frames}
    valid = [v for v in results.values() if v.get("valid")]
    if not valid:
        return {"symbol": req.symbol.upper(), "valid": False, "timeframes": results}
    readiness = [v.get("trade_readiness", 0.0) for v in valid]
    w = {"1m":0.06,"5m":0.10,"15m":0.14,"1h":0.22,"4h":0.26,"1D":0.22}
    num = sum(results[tf].get("probability_up",50.0)*w[tf] for tf in frames if results[tf].get("valid"))
    den = sum(w[tf] for tf in frames if results[tf].get("valid")) or 1.0
    p_up = num/den
    agreement = sum(1 for v in valid if (v.get("probability_up",50)>=55)==(p_up>=55)) / len(valid)
    action = "LONG" if p_up >= 58 and agreement >= 0.60 else "SHORT" if p_up <= 42 and agreement >= 0.60 else "WAIT"
    return {"symbol": req.symbol.upper(), "valid": True, "action": action, "probability_up": round(p_up,2), "probability_down": round(100-p_up,2), "agreement": round(agreement*100,2), "average_readiness": round(sum(readiness)/len(readiness),2), "timeframes": results}


@app.get("/api/news/{symbol}")
def live_news(symbol: str):
    return fetch_news(symbol)


@app.get("/api/cot/gold")
def cot_gold():
    return fetch_cot_gold()


@app.get("/api/activity")
def live_activity():
    return activity_snapshot()


@app.get("/api/oil")
def live_oil():
    return oil_snapshot()


@app.get("/api/shipping")
def live_shipping():
    return shipping_snapshot()


@app.post("/api/chat")
def quant_chat(req: ChatRequest):
    a = req.analysis or {}
    q = (req.message or "").lower().strip()
    if not a.get("valid"):
        return {"answer": "Current market feed is incomplete, so NIGHT is not forcing a directional call yet. Re-run the engine or check the data layer."}

    p_up = a.get("probability_up", 50); p_dn = a.get("probability_down", 50)
    action = a.get("action", "WAIT"); bias = a.get("bias", "NEUTRAL")
    news = a.get("news", {}); cot = a.get("cot", {}); act = a.get("activity", {})

    if any(k in q for k in ["news", "berita", "headline", "sentiment"]):
        titles = [x.get("title", "") for x in (news.get("articles") or [])[:5]]
        ans = f"Live news state is {news.get('score',0):+.2f} with event risk {a.get('event_risk',0):.0f}%. Top activity: " + " | ".join(titles)
    elif any(k in q for k in ["oil", "wti", "brent", "energy"]):
        oil=(act.get("oil") or {})
        ans = "Energy board: " + ", ".join(f"{k} {v.get('price','—')} {v.get('currency','')}" for k,v in oil.items())
    elif any(k in q for k in ["ship", "shipping", "vessel", "tanker", "container"]):
        sh=(act.get("shipping") or {})
        names=[v.get("name") or v.get("mmsi") for v in (sh.get("vessels") or [])[:8]]
        ans=f"AIS activity source {sh.get('source','—')}, tracked snapshot {sh.get('count',0)} vessels. Sample: " + ", ".join(str(x) for x in names if x)
    elif any(k in q for k in ["cot", "positioning", "managed money"]):
        latest = cot.get("latest") or {}
        ans = f"Gold positioning score {cot.get('score',0):+.2f}. Managed Money net is {latest.get('managed_money_net','—')} and the current positioning z-score is {cot.get('zscore',0):+.2f}."
    elif any(k in q for k in ["entry", "sl", "stop", "tp", "target"]):
        ans = f"Current model state is {action} with {p_up:.1f}% upside probability and {p_dn:.1f}% downside probability. Use the Execution Engine for the current entry zone, invalidation and targets; NIGHT keeps the underlying math internal."
    else:
        ans = f"{a.get('symbol')} {a.get('timeframe')}: {bias}, action {action}, upside probability {p_up:.1f}%, downside {p_dn:.1f}%, readiness {a.get('trade_readiness',0):.1f}%, confidence {a.get('confidence',0):.1f}%. News impact {news.get('score',0):+.2f}, positioning {cot.get('score',0):+.2f}."
    return {"answer": ans}


@app.get("/api/calendar")
async def calendar():
    return {"events": await macro.calendar()}


@app.get("/api/modules")
def modules():
    return {"modules": ["Live OHLCV Adapter","Exact MTF Quant","Volume/Flow","Regime","Probability/EV","FRED Macro","GDELT News Intelligence","CFTC COT Positioning","WTI/Brent/NatGas","Live AIS Shipping","Trade Readiness","Quant Chat","Report Engine"]}
