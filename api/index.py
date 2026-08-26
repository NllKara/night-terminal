from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from api.engine import analyse
from api.providers import MarketProvider, MacroProvider
from api.intelligence import intelligence_snapshot, fetch_news, fetch_cot_gold

app = FastAPI(title="NIGHT Quant Terminal API", version="0.4.0")
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
    keywords = ["federal reserve", "fed chair", "pce", "cpi", "payroll", "nfp", "war", "attack", "tariff", "hormuz", "sanction", "rate decision"]
    hits = 0
    for a in (news.get("articles") or [])[:12]:
        t = (a.get("title") or "").lower()
        hits += sum(1 for k in keywords if k in t)
    return min(82.0, 18.0 + hits * 5.0)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "night-quant-terminal", "version": "0.4.0"}


async def _analyse_one(symbol: str, timeframe: str, creds: dict):
    market_data = await market.snapshot(symbol, timeframe, creds)
    macro_data = await macro.snapshot(symbol, creds)
    intel = intelligence_snapshot(symbol)
    news = intel.get("news", {})
    cot = intel.get("cot", {})

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
    results = {}
    for tf in frames:
        results[tf] = await _analyse_one(req.symbol, tf, creds)
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
    return {
        "symbol": req.symbol.upper(), "valid": True, "action": action,
        "probability_up": round(p_up,2), "probability_down": round(100-p_up,2),
        "agreement": round(agreement*100,2), "average_readiness": round(sum(readiness)/len(readiness),2), "timeframes": results
    }


@app.get("/api/news/{symbol}")
def live_news(symbol: str):
    return fetch_news(symbol)


@app.get("/api/cot/gold")
def cot_gold():
    return fetch_cot_gold()


@app.post("/api/chat")
def quant_chat(req: ChatRequest):
    a = req.analysis or {}
    q = (req.message or "").lower().strip()
    if not a.get("valid"):
        return {"answer": "Quant engine belum punya cukup OHLCV real. Untuk XAUUSD core volume proxy sekarang bisa memakai COMEX Gold futures feed; BTCUSD bisa langsung Binance. Twelve Data/FRED tetap optional untuk enrichment."}

    p_up = a.get("probability_up", 50); p_dn = a.get("probability_down", 50); edge = a.get("edge", 0)
    math = a.get("math", {}); vp = a.get("volume_profile", {}); src = a.get("source", "unknown")
    vtype = a.get("volume_type", "unknown"); action = a.get("action", "WAIT"); bias = a.get("bias", "NEUTRAL")
    macro_details = a.get("macro_details", {}); news = a.get("news", {}); cot = a.get("cot", {})

    if any(k in q for k in ["news", "berita", "headline", "sentiment"]):
        titles = [x.get("title", "") for x in (news.get("articles") or [])[:5]]
        ans = f"News source {news.get('source','GDELT')}; score={news.get('score',0):+.3f}; event risk={a.get('event_risk',0):.1f}%. Top headlines: " + " | ".join(titles)
    elif any(k in q for k in ["cot", "positioning", "managed money"]):
        latest = cot.get("latest") or {}
        ans = f"CFTC COT score={cot.get('score',0):+.3f}, z={cot.get('zscore',0):+.2f}. Managed Money net={latest.get('managed_money_net','—')}, net/OI={latest.get('net_pct_oi','—')}."
    elif any(k in q for k in ["volume", "delta", "aggression", "buyer", "seller"]):
        ans = f"Volume source: {src}; type: {vtype}. Buyer aggression {a.get('buyer_aggression',50):.1f}% vs seller {a.get('seller_aggression',50):.1f}%. Signed-volume pressure={math.get('signed_volume_pressure',0):+.3f}, volume z={math.get('volume_z',0):+.2f}. VP: VAL={vp.get('val')}, POC={vp.get('poc')}, VAH={vp.get('vah')}."
    elif any(k in q for k in ["macro", "yield", "inflation", "fred"]):
        ans = f"Macro source: {a.get('macro_source','not configured')}. Current macro factor={a.get('components',{}).get('macro',0):+.3f}, intermarket={a.get('components',{}).get('intermarket',0):+.3f}. News={news.get('score',0):+.3f}, COT={cot.get('score',0):+.3f}. FRED z-details: {macro_details or 'none'}."
    elif any(k in q for k in ["kenapa", "why", "bias", "long", "short"]):
        ans = f"Bias {bias}, action {action}. P(up)={p_up:.1f}% and P(down)={p_dn:.1f}% from latent edge {edge:+.3f}. Trend t-stat={math.get('trend_t_stat',0):+.2f}, momentum z={math.get('momentum_z',0):+.2f}, efficiency ratio={math.get('efficiency_ratio',0):.2f}, signed-volume pressure={math.get('signed_volume_pressure',0):+.3f}, news={news.get('score',0):+.3f}, COT={cot.get('score',0):+.3f}."
    elif any(k in q for k in ["entry", "sl", "stop", "tp", "target"]):
        price = a.get("last_price"); atr_pct = math.get("atr_pct",0)
        if price and atr_pct:
            atr = price*atr_pct
            if bias == "BULLISH": stop=price-1.2*atr; tp1=price+1.5*atr; tp2=price+2.4*atr
            elif bias == "BEARISH": stop=price+1.2*atr; tp1=price-1.5*atr; tp2=price-2.4*atr
            else: return {"answer":"Bias masih neutral; model tidak memaksakan entry. Tunggu probability keluar 45–55% dan volume-flow/news/HTF mengkonfirmasi."}
            ans = f"ATR reference: current {price:.5f}, invalidation ~{stop:.5f}, target-1 ~{tp1:.5f}, target-2 ~{tp2:.5f}. Formula: 1.2×ATR stop, 1.5×/2.4×ATR targets."
        else: ans = "ATR belum tersedia."
    elif any(k in q for k in ["formula", "math", "rumus", "quant"]):
        ans = f"Core math: log returns; multi-horizon return z; OLS log-price t-stat+R²; Kaufman ER; realized vol; ATR z; volume z; signed-volume pressure; 70% VP; range structure; FRED macro; GDELT headline score; CFTC managed-money positioning; weighted latent edge; logistic probability; EV. Current edge={edge:+.3f}, EV long={a.get('ev_long_r',0):+.3f}R, EV short={a.get('ev_short_r',0):+.3f}R."
    else:
        ans = f"{a.get('symbol')} {a.get('timeframe')}: {bias}, action {action}, P(up) {p_up:.1f}%, P(down) {p_dn:.1f}%, readiness {a.get('trade_readiness',0):.1f}%, confidence {a.get('confidence',0):.1f}%. News {news.get('score',0):+.3f}, COT {cot.get('score',0):+.3f}."
    return {"answer": ans}


@app.get("/api/calendar")
async def calendar():
    return {"events": await macro.calendar()}


@app.get("/api/modules")
def modules():
    return {"modules": ["Live OHLCV Adapter","Exact MTF Quant","Quant Trend","Momentum Z","OLS t-stat","Kaufman ER","Realized Volatility","ATR Z","Volume Z","Signed Volume Pressure","Volume Profile","Liquidity/Structure","FRED Macro","GDELT News Intelligence","CFTC COT Positioning","Probability Model","Expected Value","Conflict Penalty","Trade Readiness","Quant Chat","Institutional PDF Report"]}
