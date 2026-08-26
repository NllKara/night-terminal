from __future__ import annotations

import math
import statistics
from typing import Dict, List


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def mean(xs: List[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def stdev(xs: List[float]) -> float:
    return statistics.stdev(xs) if len(xs) > 1 else 0.0


def zscore(x: float, xs: List[float]) -> float:
    s = stdev(xs)
    return 0.0 if s == 0 else (x - mean(xs)) / s


def log_returns(closes: List[float]) -> List[float]:
    out = []
    for a, b in zip(closes[:-1], closes[1:]):
        if a > 0 and b > 0:
            out.append(math.log(b / a))
    return out


def linreg_t(values: List[float]) -> Dict[str, float]:
    n = len(values)
    if n < 5:
        return {"slope": 0.0, "t": 0.0, "r2": 0.0}
    x = list(range(n))
    xm = mean(x); ym = mean(values)
    sxx = sum((v - xm) ** 2 for v in x)
    sxy = sum((x[i] - xm) * (values[i] - ym) for i in range(n))
    if sxx == 0:
        return {"slope": 0.0, "t": 0.0, "r2": 0.0}
    slope = sxy / sxx
    intercept = ym - slope * xm
    fitted = [intercept + slope * v for v in x]
    resid = [values[i] - fitted[i] for i in range(n)]
    sse = sum(v * v for v in resid)
    sst = sum((v - ym) ** 2 for v in values)
    r2 = 0.0 if sst == 0 else max(0.0, 1.0 - sse / sst)
    sigma2 = sse / max(1, n - 2)
    se = math.sqrt(sigma2 / sxx) if sigma2 > 0 else 0.0
    t = 0.0 if se == 0 else slope / se
    return {"slope": slope, "t": t, "r2": r2}


def efficiency_ratio(closes: List[float], n: int = 20) -> float:
    if len(closes) < n + 1:
        return 0.0
    xs = closes[-(n + 1):]
    direction = abs(xs[-1] - xs[0])
    noise = sum(abs(b - a) for a, b in zip(xs[:-1], xs[1:]))
    return 0.0 if noise == 0 else direction / noise


def true_ranges(bars: List[dict]) -> List[float]:
    out = []
    prev_close = None
    for b in bars:
        h, l, c = b["high"], b["low"], b["close"]
        tr = h - l if prev_close is None else max(h - l, abs(h - prev_close), abs(l - prev_close))
        out.append(tr)
        prev_close = c
    return out


def volume_profile(bars: List[dict], bins: int = 30) -> dict:
    if not bars:
        return {"vah": None, "poc": None, "val": None, "position": 0.0}
    lo = min(b["low"] for b in bars)
    hi = max(b["high"] for b in bars)
    if hi <= lo:
        p = bars[-1]["close"]
        return {"vah": p, "poc": p, "val": p, "position": 0.0}
    width = (hi - lo) / bins
    profile = [0.0] * bins
    for b in bars:
        typical = (b["high"] + b["low"] + b["close"]) / 3.0
        idx = min(bins - 1, max(0, int((typical - lo) / width)))
        profile[idx] += max(0.0, float(b.get("volume", 0.0)))
    total = sum(profile)
    if total <= 0:
        return {"vah": None, "poc": None, "val": None, "position": 0.0}
    poc_i = max(range(bins), key=lambda i: profile[i])
    chosen = {poc_i}; covered = profile[poc_i]
    left, right = poc_i - 1, poc_i + 1
    target = total * 0.70
    while covered < target and (left >= 0 or right < bins):
        lv = profile[left] if left >= 0 else -1
        rv = profile[right] if right < bins else -1
        if rv > lv:
            chosen.add(right); covered += max(0.0, rv); right += 1
        else:
            chosen.add(left); covered += max(0.0, lv); left -= 1
    val_i, vah_i = min(chosen), max(chosen)
    price = bars[-1]["close"]
    poc = lo + (poc_i + 0.5) * width
    val = lo + val_i * width
    vah = lo + (vah_i + 1) * width
    pos = (price - poc) / max(width, 1e-12)
    return {"vah": vah, "poc": poc, "val": val, "position": pos}


def signed_volume_pressure(bars: List[dict], n: int = 20) -> float:
    xs = bars[-n:]
    den = sum(max(0.0, float(b.get("volume", 0.0))) for b in xs)
    if den <= 0:
        return 0.0
    num = 0.0
    for b in xs:
        rng = max(b["high"] - b["low"], 1e-12)
        location = ((b["close"] - b["open"]) / rng)
        num += float(b.get("volume", 0.0)) * max(-1.0, min(1.0, location))
    return max(-1.0, min(1.0, num / den))


def calculate_quant(bars: List[dict], macro: Dict[str, float] | None = None, event_risk: float = 20.0, source: str = "unknown", volume_type: str = "unknown") -> dict:
    macro = macro or {}
    if len(bars) < 30:
        return {
            "valid": False,
            "reason": "Need at least 30 OHLCV candles for quant analysis.",
            "data_quality": 0,
            "source": source,
            "volume_type": volume_type,
        }

    closes = [float(b["close"]) for b in bars]
    vols = [float(b.get("volume", 0.0)) for b in bars]
    rets = log_returns(closes)
    recent_rets = rets[-30:]
    sigma = stdev(recent_rets) or 1e-12

    # 1) multi-horizon standardized momentum
    h5 = sum(rets[-5:]) / (sigma * math.sqrt(5)) if len(rets) >= 5 else 0.0
    h15 = sum(rets[-15:]) / (sigma * math.sqrt(15)) if len(rets) >= 15 else 0.0
    momentum_z = 0.65 * h5 + 0.35 * h15

    # 2) OLS trend significance on log-price
    logp = [math.log(max(x, 1e-12)) for x in closes[-40:]]
    reg = linreg_t(logp)
    trend_t = reg["t"]

    # 3) Kaufman efficiency ratio: 0 noisy/range -> 1 directional
    er = efficiency_ratio(closes, 20)

    # 4) realized volatility + relative ATR
    rv = sigma * math.sqrt(252 * 24 * 12)  # normalized reference for intraday; used comparatively
    trs = true_ranges(bars)
    atr = mean(trs[-14:])
    atr_pct = atr / max(closes[-1], 1e-12)
    atr_hist = [mean(trs[max(0, i-13):i+1]) / max(closes[i], 1e-12) for i in range(max(13, len(bars)-60), len(bars))]
    atr_z = zscore(atr_pct, atr_hist[:-1]) if len(atr_hist) > 2 else 0.0

    # 5) standardized current volume and signed volume-pressure proxy
    vol_z = zscore(vols[-1], vols[-31:-1]) if len(vols) >= 31 else 0.0
    svp = signed_volume_pressure(bars, 20)

    # 6) volume profile from observed candle volume/tick-volume
    vp = volume_profile(bars[-120:], 32)
    vp_score = math.tanh(vp["position"] / 4.0) if vp["poc"] is not None else 0.0

    # 7) structure: normalized location inside rolling 20-bar range
    h20 = max(b["high"] for b in bars[-20:]); l20 = min(b["low"] for b in bars[-20:])
    structure = 0.0 if h20 == l20 else 2.0 * ((closes[-1] - l20) / (h20 - l20)) - 1.0
    structure = max(-1.0, min(1.0, structure))

    # 8) macro/intermarket inputs are already normalized [-1, +1]
    macro_score = max(-1.0, min(1.0, float(macro.get("macro_score", 0.0))))
    intermarket = max(-1.0, min(1.0, float(macro.get("intermarket_score", 0.0))))

    # Squash unbounded statistics to [-1,+1]
    mom_s = math.tanh(momentum_z / 2.0)
    trend_s = math.tanh(trend_t / 3.0) * (0.45 + 0.55 * er)
    volflow_s = math.tanh(vol_z / 2.0) * 0.35 + svp * 0.65

    # Composite latent edge. Weights sum to 1.
    components = {
        "momentum": mom_s,
        "trend": trend_s,
        "structure": structure,
        "volume_flow": volflow_s,
        "volume_profile": vp_score,
        "macro": macro_score,
        "intermarket": intermarket,
    }
    weights = {
        "momentum": 0.18,
        "trend": 0.20,
        "structure": 0.12,
        "volume_flow": 0.20,
        "volume_profile": 0.10,
        "macro": 0.10,
        "intermarket": 0.10,
    }
    edge = sum(components[k] * weights[k] for k in components)

    # Disagreement penalty: higher dispersion among directional factors -> lower confidence.
    dispersion = stdev(list(components.values()))
    conflict = clamp(dispersion / 0.85 * 100.0)

    # Probability via logistic mapping of latent edge.
    p_up = sigmoid(3.2 * edge)
    p_down = 1.0 - p_up

    # Expected value for a canonical 1.5R target / 1R risk before costs.
    rr = 1.5
    ev_long = p_up * rr - p_down
    ev_short = p_down * rr - p_up

    has_volume = sum(vols[-20:]) > 0
    freshness = float(macro.get("freshness", 1.0))
    dq = 55.0 + (20.0 if has_volume else -20.0) + 15.0 * max(0.0, min(1.0, freshness))
    dq -= min(25.0, float(event_risk) * 0.18)
    data_quality = clamp(dq)

    confidence = clamp(100.0 * abs(p_up - 0.5) * 2.0 * (0.55 + 0.45 * data_quality / 100.0) * (1.0 - min(conflict, 90.0) / 180.0))

    edge_strength = abs(edge)
    readiness = clamp(
        100.0 * (
            0.48 * min(1.0, edge_strength / 0.45) +
            0.22 * data_quality / 100.0 +
            0.15 * min(1.0, er / 0.55) +
            0.15 * min(1.0, abs(volflow_s))
        ) - float(event_risk) * 0.28 - conflict * 0.10
    )

    if not has_volume or data_quality < 35:
        action = "NO TRADE"
    elif float(event_risk) >= 85:
        action = "NO TRADE"
    elif p_up >= 0.58 and ev_long > 0.10 and readiness >= 48:
        action = "LONG"
    elif p_down >= 0.58 and ev_short > 0.10 and readiness >= 48:
        action = "SHORT"
    else:
        action = "WAIT"

    bias = "BULLISH" if p_up >= 0.55 else "BEARISH" if p_up <= 0.45 else "NEUTRAL"
    regime = "TREND" if abs(trend_t) >= 2.0 and er >= 0.35 else "VOLATILE" if atr_z >= 1.0 else "RANGE"
    aggression = clamp(50.0 + 50.0 * svp)
    greed = clamp(50.0 + 22.0 * mom_s + 18.0 * trend_s + 10.0 * max(-1.0, min(1.0, atr_z / 2.0)))

    return {
        "valid": True,
        "source": source,
        "volume_type": volume_type,
        "last_price": closes[-1],
        "bias": bias,
        "action": action,
        "regime": regime,
        "score": round(50.0 + edge * 50.0, 2),
        "edge": round(edge, 4),
        "probability_up": round(p_up * 100.0, 2),
        "probability_down": round(p_down * 100.0, 2),
        "ev_long_r": round(ev_long, 3),
        "ev_short_r": round(ev_short, 3),
        "confidence": round(confidence, 2),
        "trade_readiness": round(readiness, 2),
        "buyer_aggression": round(aggression, 2),
        "seller_aggression": round(100.0 - aggression, 2),
        "greed": round(greed, 2),
        "event_risk": round(float(event_risk), 2),
        "volatility": round(clamp(50 + 16 * atr_z), 2),
        "data_quality": round(data_quality, 2),
        "conflict": round(conflict, 2),
        "volume_profile": {k: (round(v, 5) if isinstance(v, (int, float)) and v is not None else v) for k, v in vp.items()},
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "math": {
            "momentum_z": round(momentum_z, 4),
            "trend_t_stat": round(trend_t, 4),
            "trend_r2": round(reg["r2"], 4),
            "efficiency_ratio": round(er, 4),
            "realized_vol": round(rv, 6),
            "atr_pct": round(atr_pct, 6),
            "atr_z": round(atr_z, 4),
            "volume_z": round(vol_z, 4),
            "signed_volume_pressure": round(svp, 4),
            "structure_location": round(structure, 4),
        },
        "formula": "edge=Σ(w_i*x_i); p_up=sigmoid(3.2*edge); EV_long=1.5*p_up-(1-p_up); confidence penalizes factor dispersion; readiness combines edge strength, data quality, efficiency ratio, volume-flow, event/conflict penalties.",
        "scenario": f"{bias.title()} {regime.lower()} regime. Quant edge {edge:+.3f}; P(up) {p_up*100:.1f}%; P(down) {p_down*100:.1f}%.",
        "invalidation": "Thesis weakens when composite edge crosses zero, probability returns inside 45–55%, or volume-flow/trend signs reverse together.",
    }


def analyse(symbol: str, timeframe: str, inputs: Dict) -> dict:
    bars = inputs.get("bars") or []
    result = calculate_quant(
        bars,
        macro=inputs.get("macro") or {},
        event_risk=float(inputs.get("event_risk", 20.0)),
        source=inputs.get("source", "unknown"),
        volume_type=inputs.get("volume_type", "unknown"),
    )
    result.update({"symbol": symbol.upper(), "timeframe": timeframe})
    return result
