from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from api.engine import analyse
from api.providers import MarketProvider, MacroProvider

app = FastAPI(title="NIGHT Quant Terminal API", version="0.2.0")
market = MarketProvider()
macro = MacroProvider()


class Credentials(BaseModel):
    twelve_key: str | None = None
    oanda_token: str | None = None
    oanda_account: str | None = None


class AnalysisRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "5m"
    credentials: Credentials | None = None


class ChatRequest(BaseModel):
    message: str
    analysis: dict


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "night-quant-terminal", "version": "0.2.0"}


@app.post("/api/analyse")
async def run_analysis(req: AnalysisRequest):
    creds = req.credentials.model_dump(exclude_none=True) if req.credentials else {}
    market_data = await market.snapshot(req.symbol, req.timeframe, creds)
    macro_data = await macro.snapshot(req.symbol, creds)
    payload = {
        **market_data,
        "macro": macro_data,
        "event_risk": 20.0,
    }
    result = analyse(req.symbol, req.timeframe, payload)
    result["provider_errors"] = market_data.get("provider_errors", [])
    return result


@app.post("/api/chat")
def quant_chat(req: ChatRequest):
    a = req.analysis or {}
    q = (req.message or "").lower().strip()
    if not a.get("valid"):
        return {"answer": "Quant engine belum punya cukup OHLCV real. Masukkan OANDA practice token/account untuk FX/XAU, atau Twelve Data free API key. BTCUSD bisa jalan langsung dari Binance tanpa key."}

    p_up = a.get("probability_up", 50)
    p_dn = a.get("probability_down", 50)
    edge = a.get("edge", 0)
    math = a.get("math", {})
    vp = a.get("volume_profile", {})
    src = a.get("source", "unknown")
    vtype = a.get("volume_type", "unknown")
    action = a.get("action", "WAIT")
    bias = a.get("bias", "NEUTRAL")

    if any(k in q for k in ["volume", "delta", "aggression", "buyer", "seller"]):
        ans = (
            f"Volume source: {src}; type: {vtype}. Buyer aggression {a.get('buyer_aggression', 50):.1f}% vs seller {a.get('seller_aggression', 50):.1f}%. "
            f"Signed-volume pressure={math.get('signed_volume_pressure', 0):+.3f}, volume z-score={math.get('volume_z', 0):+.2f}. "
            f"VP: VAL={vp.get('val')}, POC={vp.get('poc')}, VAH={vp.get('vah')}."
        )
    elif any(k in q for k in ["kenapa", "why", "bias", "long", "short"]):
        ans = (
            f"Bias {bias}, action {action}. Model gives P(up)={p_up:.1f}% and P(down)={p_dn:.1f}% from latent edge {edge:+.3f}. "
            f"Trend t-stat={math.get('trend_t_stat', 0):+.2f}, momentum z={math.get('momentum_z', 0):+.2f}, "
            f"efficiency ratio={math.get('efficiency_ratio', 0):.2f}, signed-volume pressure={math.get('signed_volume_pressure', 0):+.3f}."
        )
    elif any(k in q for k in ["entry", "sl", "stop", "tp", "target"]):
        price = a.get("last_price")
        atr_pct = math.get("atr_pct", 0)
        if price and atr_pct:
            atr = price * atr_pct
            if bias == "BULLISH":
                stop = price - 1.2 * atr; tp1 = price + 1.5 * atr; tp2 = price + 2.4 * atr
            elif bias == "BEARISH":
                stop = price + 1.2 * atr; tp1 = price - 1.5 * atr; tp2 = price - 2.4 * atr
            else:
                return {"answer": "Bias masih neutral, jadi model tidak memaksakan entry. Tunggu probability keluar dari zona 45–55% dan volume-flow mengkonfirmasi."}
            ans = f"ATR-based reference only: current {price:.5f}, invalidation ~{stop:.5f}, target-1 ~{tp1:.5f}, target-2 ~{tp2:.5f}. Ini dihitung 1.2×ATR stop dan 1.5×/2.4×ATR targets, bukan signal pasti."
        else:
            ans = "ATR belum tersedia dari data saat ini."
    elif any(k in q for k in ["formula", "math", "rumus", "quant"]):
        ans = (
            "Core math: log returns; multi-horizon return z-score; OLS log-price slope t-stat + R²; Kaufman efficiency ratio; realized volatility; ATR z-score; "
            "volume z-score; signed-volume pressure; 70% volume-profile POC/VAH/VAL; rolling structure location; weighted latent edge; logistic probability; expected R. "
            f"Current edge={edge:+.3f}, EV long={a.get('ev_long_r',0):+.3f}R, EV short={a.get('ev_short_r',0):+.3f}R."
        )
    else:
        ans = (
            f"{a.get('symbol')} {a.get('timeframe')}: {bias}, action {action}, P(up) {p_up:.1f}%, P(down) {p_dn:.1f}%, "
            f"readiness {a.get('trade_readiness',0):.1f}%, confidence {a.get('confidence',0):.1f}%. Ask me about volume, bias, entry/SL/TP, or formulas."
        )
    return {"answer": ans}


@app.get("/api/calendar")
async def calendar():
    return {"events": await macro.calendar()}


@app.get("/api/modules")
def modules():
    return {"modules": [
        "Live OHLCV Adapter", "Quant Trend", "Momentum Z", "OLS t-stat", "Kaufman ER",
        "Realized Volatility", "ATR Z", "Volume Z", "Signed Volume Pressure", "Volume Profile",
        "Liquidity/Structure", "Probability Model", "Expected Value", "Conflict Penalty",
        "Trade Readiness", "Quant Chat", "Macro/Intermarket adapters"
    ]}
