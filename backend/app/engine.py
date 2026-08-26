from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Factor:
    score: float
    weight: float


def clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def analyse(symbol: str, timeframe: str, inputs: Dict[str, float]) -> dict:
    """Transparent deterministic engine. Replace/augment inputs with real providers later."""
    factors = {
        "trend": Factor(inputs.get("trend", 50), 0.18),
        "structure": Factor(inputs.get("structure", 50), 0.14),
        "volume": Factor(inputs.get("volume", 50), 0.16),
        "aggression": Factor(inputs.get("aggression", 50), 0.12),
        "macro": Factor(inputs.get("macro", 50), 0.16),
        "intermarket": Factor(inputs.get("intermarket", 50), 0.10),
        "session": Factor(inputs.get("session", 50), 0.06),
        "liquidity": Factor(inputs.get("liquidity", 50), 0.08),
    }
    composite = sum(x.score * x.weight for x in factors.values())
    event_risk = clamp(inputs.get("event_risk", 20))
    volatility = clamp(inputs.get("volatility", 50))
    data_quality = clamp(inputs.get("data_quality", 75))
    conflict = clamp(inputs.get("conflict", 25))

    confidence = clamp(composite * 0.72 + data_quality * 0.28 - conflict * 0.22)
    readiness = clamp(confidence - event_risk * 0.25 + min(volatility, 70) * 0.08)
    greed = clamp(inputs.get("greed", factors["aggression"].score * 0.55 + factors["volume"].score * 0.45))

    if composite >= 62:
        bias = "BULLISH"
    elif composite <= 38:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    if readiness < 52 or event_risk > 78:
        action = "NO TRADE"
    elif readiness >= 72 and bias != "NEUTRAL":
        action = "HIGH CONVICTION"
    elif bias != "NEUTRAL":
        action = "WAIT FOR CONFIRMATION"
    else:
        action = "NO TRADE"

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "bias": bias,
        "action": action,
        "score": round(composite, 1),
        "confidence": round(confidence, 1),
        "trade_readiness": round(readiness, 1),
        "greed": round(greed, 1),
        "buyer_aggression": round(factors["aggression"].score, 1),
        "event_risk": round(event_risk, 1),
        "volatility": round(volatility, 1),
        "data_quality": round(data_quality, 1),
        "factors": {k: round(v.score, 1) for k, v in factors.items()},
        "scenario": f"{bias.title()} conditions dominate. Require price/volume confirmation before execution.",
        "invalidation": "Invalidate directional thesis when structure, volume acceptance and macro/intermarket confirmation materially flip.",
        "warnings": [
            "Do not treat a score as certainty.",
            "Reduce confidence around high-impact events and stale/incomplete feeds."
        ],
    }
