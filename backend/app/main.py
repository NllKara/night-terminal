from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .engine import analyse
from .providers import MarketProvider, MacroProvider

app = FastAPI(title="NIGHT Terminal API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
market = MarketProvider()
macro = MacroProvider()


class AnalysisRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "5m"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyse")
async def run_analysis(req: AnalysisRequest):
    market_data = await market.snapshot(req.symbol, req.timeframe)
    macro_data = await macro.snapshot(req.symbol)
    return analyse(req.symbol, req.timeframe, {**market_data, **macro_data})


@app.get("/api/calendar")
async def calendar():
    return {"events": await macro.calendar()}


@app.get("/api/modules")
def modules():
    return {"modules": [
        "Market Structure", "Trend Regime", "Volume Profile", "Aggression/Delta",
        "Liquidity", "Volatility", "Macro Economy", "Economic Calendar",
        "Intermarket", "Session Context", "Sentiment/Greed", "Trade Readiness",
        "Scenario Engine", "Invalidation Engine", "Risk Guard"
    ]}
