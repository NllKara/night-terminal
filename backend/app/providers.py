from datetime import datetime, timezone
import hashlib


def _seed(symbol: str, key: str) -> float:
    raw = hashlib.sha256(f"{symbol}:{key}".encode()).hexdigest()
    return 30 + (int(raw[:8], 16) % 4100) / 100


class MarketProvider:
    """Development provider. Swap methods for Twelve Data/Polygon/broker feeds/etc."""
    async def snapshot(self, symbol: str, timeframe: str) -> dict:
        return {
            "trend": _seed(symbol, "trend"),
            "structure": _seed(symbol, "structure"),
            "volume": _seed(symbol, "volume"),
            "aggression": _seed(symbol, "aggression"),
            "liquidity": _seed(symbol, "liquidity"),
            "volatility": _seed(symbol, "volatility"),
            "data_quality": 72,
        }


class MacroProvider:
    async def snapshot(self, symbol: str) -> dict:
        return {
            "macro": _seed(symbol, "macro"),
            "intermarket": _seed(symbol, "intermarket"),
            "event_risk": 28,
            "session": 62,
            "conflict": 24,
        }

    async def calendar(self) -> list:
        now = datetime.now(timezone.utc).isoformat()
        return [
            {"time": now, "currency": "USD", "event": "Calendar provider not configured", "impact": "INFO", "forecast": "—", "previous": "—"}
        ]
