from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from api.engine import analyse
from api.providers import MarketProvider, MacroProvider

app = FastAPI(title="NIGHT Quant Terminal API", version="0.3.0")
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


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "night-quant-terminal", "version": "0.3.0"}


async def _analyse_one(symbol: str, timeframe: str, creds: dict):
    market_data = await market.snapshot(symbol, timeframe, creds)
    macro_data = await macro.snapshot(symbol, creds)
    payload = {**market_data, "macro": macro_data, "event_risk": 20.0}
    result = analyse(symbol, timeframe, payload)
    result["provider_errors"] = market_data.get("provider_errors", [])
    result["macro_source"] = macro_data.get("macro_source")
    result["macro_details"] = macro_data.get("macro_details", {})
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
    probs = [v.get("probability_up", 50.0) for v in valid]
    readiness = [v.get("trade_readiness", 0.0) for v in valid]
    # HTF-weighted aggregate probability, LTF kept for timing rather than dominating direction.
    w = {"1m":0.06,"5m":0.10,"15m":0.14,"1h":0.22,"4h":0.26,"1D":0.22}
    num = sum(results[tf].get("probability_up",50.0)*w[tf] for tf in frames if results[tf].get("valid"))
    den = sum(w[tf] for tf in frames if results[tf].get("valid")) or 1.0
    p_up = num/den
    agreement = sum(1 for v in valid if (v.get("probability_up",50)>=55)==(p_up>=55)) / len(valid)
    return {
        "symbol": req.symbol.upper(), "valid": True, "probability_up": round(p_up,2), "probability_down": round(100-p_up,2),
        "agreement": round(agreement*100,2), "average_readiness": round(sum(readiness)/len(readiness),2), "timeframes": results
    }


@app.post("/api/chat")
def quant_chat(req: ChatRequest):
    a = req.analysis or {}
    q = (req.message or "").lower().strip()
    if not a.get("valid"):
        return {"answer": "Quant engine belum punya cukup OHLCV real. Untuk XAU/FX pakai OANDA practice token atau Twelve Data free key. BTCUSD bisa jalan langsung dari Binance public data tanpa key."}

    p_up = a.get("probability_up", 50); p_dn = a.get("probability_down", 50); edge = a.get("edge", 0)
    math = a.get("math", {}); vp = a.get("volume_profile", {}); src = a.get("source", "unknown")
    vtype = a.get("volume_type", "unknown"); action = a.get("action", "WAIT"); bias = a.get("bias", "NEUTRAL")
    macro_details = a.get("macro_details", {})

    if any(k in q for k in ["volume", "delta", "aggression", "buyer", "seller"]):
        ans = f"Volume source: {src}; type: {vtype}. Buyer aggression {a.get('buyer_aggression',50):.1f}% vs seller {a.get('seller_aggression',50):.1f}%. Signed-volume pressure={math.get('signed_volume_pressure',0):+.3f}, volume z={math.get('volume_z',0):+.2f}. VP: VAL={vp.get('val')}, POC={vp.get('poc')}, VAH={vp.get('vah')}."
    elif any(k in q for k in ["macro", "yield", "inflation", "fred"]):
        ans = f"Macro source: {a.get('macro_source','not configured')}. Current macro factor={a.get('components',{}).get('macro',0):+.3f}, intermarket={a.get('components',{}).get('intermarket',0):+.3f}. FRED z-details: {macro_details or 'none'}."
    elif any(k in q for k in ["kenapa", "why", "bias", "long", "short"]):
        ans = f"Bias {bias}, action {action}. P(up)={p_up:.1f}% and P(down)={p_dn:.1f}% from latent edge {edge:+.3f}. Trend t-stat={math.get('trend_t_stat',0):+.2f}, momentum z={math.get('momentum_z',0):+.2f}, efficiency ratio={math.get('efficiency_ratio',0):.2f}, signed-volume pressure={math.get('signed_volume_pressure',0):+.3f}."
    elif any(k in q for k in ["entry", "sl", "stop", "tp", "target"]):
        price = a.get("last_price"); atr_pct = math.get("atr_pct",0)
        if price and atr_pct:
            atr = price*atr_pct
            if bias == "BULLISH": stop=price-1.2*atr; tp1=price+1.5*atr; tp2=price+2.4*atr
            elif bias == "BEARISH": stop=price+1.2*atr; tp1=price-1.5*atr; tp2=price-2.4*atr
            else: return {"answer":"Bias masih neutral; model tidak memaksakan entry. Tunggu probability keluar 45–55% dan volume-flow mengkonfirmasi."}
            ans = f"ATR reference: current {price:.5f}, invalidation ~{stop:.5f}, target-1 ~{tp1:.5f}, target-2 ~{tp2:.5f}. Formula: 1.2×ATR stop, 1.5×/2.4×ATR targets."
        else: ans = "ATR belum tersedia."
    elif any(k in q for k in ["formula", "math", "rumus", "quant"]):
        ans = f"Core math: log returns; multi-horizon return z; OLS log-price t-stat+R²; Kaufman ER; realized vol; ATR z; volume z; signed-volume pressure; 70% VP; range structure; weighted latent edge; logistic probability; EV. Current edge={edge:+.3f}, EV long={a.get('ev_long_r',0):+.3f}R, EV short={a.get('ev_short_r',0):+.3f}R."
    else:
        ans = f"{a.get('symbol')} {a.get('timeframe')}: {bias}, action {action}, P(up) {p_up:.1f}%, P(down) {p_dn:.1f}%, readiness {a.get('trade_readiness',0):.1f}%, confidence {a.get('confidence',0):.1f}%. Ask about volume, macro, bias, entry/SL/TP, or formulas."
    return {"answer": ans}


@app.get("/api/calendar")
async def calendar():
    return {"events": await macro.calendar()}


@app.get("/api/modules")
def modules():
    return {"modules": ["Live OHLCV Adapter","Exact MTF Quant","Quant Trend","Momentum Z","OLS t-stat","Kaufman ER","Realized Volatility","ATR Z","Volume Z","Signed Volume Pressure","Volume Profile","Liquidity/Structure","FRED Macro","Probability Model","Expected Value","Conflict Penalty","Trade Readiness","Quant Chat"]}
