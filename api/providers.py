from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


def _get_json(url: str, headers: dict | None = None, timeout: int = 12):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "NIGHT-Terminal/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _interval_map(tf: str) -> str:
    return {
        "1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h",
        "4h": "4h", "1D": "1day", "1d": "1day"
    }.get(tf, "5min")


def _oanda_granularity(tf: str) -> str:
    return {"1m": "M1", "5m": "M5", "15m": "M15", "1h": "H1", "4h": "H4", "1D": "D", "1d": "D"}.get(tf, "M5")


def _symbol_td(symbol: str) -> str:
    m = {
        "XAUUSD": "XAU/USD", "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY", "BTCUSD": "BTC/USD"
    }
    return m.get(symbol.upper(), symbol.upper())


def _symbol_oanda(symbol: str) -> str:
    m = {"XAUUSD": "XAU_USD", "EURUSD": "EUR_USD", "GBPUSD": "GBP_USD", "USDJPY": "USD_JPY"}
    return m.get(symbol.upper(), symbol.upper())


def _binance_symbol(symbol: str) -> str | None:
    return {"BTCUSD": "BTCUSDT"}.get(symbol.upper())


class MarketProvider:
    async def snapshot(self, symbol: str, timeframe: str, credentials: dict | None = None) -> dict:
        credentials = credentials or {}
        errors = []

        # 1) OANDA: best free route for FX/metals tick-volume if user has a free practice token/account.
        token = credentials.get("oanda_token") or os.environ.get("OANDA_TOKEN")
        account = credentials.get("oanda_account") or os.environ.get("OANDA_ACCOUNT_ID")
        if token and account and symbol.upper() in {"XAUUSD", "EURUSD", "GBPUSD", "USDJPY"}:
            try:
                inst = _symbol_oanda(symbol)
                params = urllib.parse.urlencode({"granularity": _oanda_granularity(timeframe), "count": 180, "price": "M"})
                url = f"https://api-fxpractice.oanda.com/v3/instruments/{inst}/candles?{params}"
                data = _get_json(url, {"Authorization": f"Bearer {token}", "User-Agent": "NIGHT-Terminal/1.0"})
                bars = []
                for c in data.get("candles", []):
                    mid = c.get("mid") or {}
                    if not mid:
                        continue
                    bars.append({
                        "time": c.get("time"), "open": float(mid["o"]), "high": float(mid["h"]),
                        "low": float(mid["l"]), "close": float(mid["c"]), "volume": float(c.get("volume", 0))
                    })
                if len(bars) >= 30:
                    return {"bars": bars, "source": "OANDA practice v20", "volume_type": "tick volume (price-update count)", "freshness": 1.0}
                errors.append("OANDA returned too few candles")
            except Exception as e:
                errors.append(f"OANDA: {type(e).__name__}")

        # 2) Binance public REST: actual exchange-traded volume, no key needed for supported crypto.
        bsym = _binance_symbol(symbol)
        if bsym:
            try:
                interval = {"1m":"1m","5m":"5m","15m":"15m","1h":"1h","4h":"4h","1D":"1d","1d":"1d"}.get(timeframe,"5m")
                url = f"https://api.binance.com/api/v3/klines?symbol={bsym}&interval={interval}&limit=180"
                rows = _get_json(url)
                bars = [{
                    "time": r[0], "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
                    "close": float(r[4]), "volume": float(r[5])
                } for r in rows]
                if len(bars) >= 30:
                    return {"bars": bars, "source": "Binance public market data", "volume_type": "exchange traded base-asset volume", "freshness": 1.0}
            except Exception as e:
                errors.append(f"Binance: {type(e).__name__}")

        # 3) Twelve Data Basic: free real-time FX/crypto via REST; metals availability depends on plan/symbol access.
        td_key = credentials.get("twelve_key") or os.environ.get("TWELVE_DATA_API_KEY")
        if td_key:
            try:
                params = urllib.parse.urlencode({
                    "symbol": _symbol_td(symbol), "interval": _interval_map(timeframe),
                    "outputsize": 180, "apikey": td_key, "format": "JSON"
                })
                data = _get_json(f"https://api.twelvedata.com/time_series?{params}")
                if data.get("status") == "error":
                    raise RuntimeError(data.get("message", "Twelve Data error"))
                values = list(reversed(data.get("values", [])))
                bars = []
                for r in values:
                    bars.append({
                        "time": r.get("datetime"), "open": float(r["open"]), "high": float(r["high"]),
                        "low": float(r["low"]), "close": float(r["close"]), "volume": float(r.get("volume") or 0)
                    })
                if len(bars) >= 30:
                    vol_type = "provider volume" if sum(b["volume"] for b in bars[-20:]) > 0 else "unavailable for this feed"
                    return {"bars": bars, "source": "Twelve Data Basic/REST", "volume_type": vol_type, "freshness": 0.95}
                errors.append("Twelve Data returned too few candles")
            except Exception as e:
                errors.append(f"Twelve Data: {type(e).__name__}")

        return {"bars": [], "source": "none", "volume_type": "none", "freshness": 0.0, "provider_errors": errors}


class MacroProvider:
    async def snapshot(self, symbol: str, credentials: dict | None = None) -> dict:
        # Macro connector is intentionally neutral until live series are configured; this prevents fabricated macro scores.
        return {"macro_score": 0.0, "intermarket_score": 0.0, "freshness": 1.0}

    async def calendar(self) -> list:
        return [{
            "time": None, "currency": "USD", "event": "Use the embedded TradingView calendar now; API calendar connector pending",
            "impact": "INFO", "forecast": "—", "previous": "—"
        }]
