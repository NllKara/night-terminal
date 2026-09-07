from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional

MODEL_LIBRARY = {
    "valuation_parity_arbitrage": [
        "Covered Interest Rate Parity (CIRP)",
        "Uncovered Interest Rate Parity (UIRP)",
        "Purchasing Power Parity (PPP)",
        "Real Interest Rate Differential (RIRD) Model",
        "Triangular Arbitrage Matrix",
        "Cross-Currency Basis Swap Pricing Model",
    ],
    "stochastic_options_volatility": [
        "Geometric Brownian Motion (GBM)",
        "Black-Scholes Model (Forex Garman-Kohlhagen Extension)",
        "Heston Stochastic Volatility Model",
        "SABR Volatility Model",
        "Garman-Klass Volatility Estimator",
        "Parkinsons Volatility Estimator",
        "Yang-Zhang Volatility Estimator",
        "GARCH (Generalized Autoregressive Conditional Heteroskedasticity)",
        "EGARCH & TGARCH (Asymmetric Volatility Models)",
        "Implied Volatility Surface Interpolation (SVI / Cubic Spline)",
    ],
    "stat_arb_mean_reversion_econometrics": [
        "Augmented Dickey-Fuller (ADF) Test",
        "Johansen Cointegration Test",
        "Engle-Granger Two-Step Cointegration Test",
        "Z-Score Calculation",
        "Ornstein-Uhlenbeck (OU) Process",
        "Half-Life of Mean Reversion Equation",
        "Hurst Exponent",
        "Vector Autoregression (VAR) Model",
        "Error Correction Model (ECM)",
    ],
    "signal_processing_time_series_ml": [
        "Autoregressive Integrated Moving Average (ARIMA)",
        "SARIMAX (Seasonal ARIMA with Exogenous Variables)",
        "Kalman Filter",
        "Extended / Unscented Kalman Filter",
        "Fast Fourier Transform (FFT)",
        "Wavelet Transform",
        "Hidden Markov Model (HMM)",
        "Principal Component Analysis (PCA)",
        "Exponential Smoothing (Holt-Winters)",
    ],
    "execution_microstructure_hft": [
        "Volume-Weighted Average Price (VWAP)",
        "Time-Weighted Average Price (TWAP)",
        "Almgren-Chriss Optimal Execution Model",
        "Kyle’s Lambda (Market Impact Estimator)",
        "Amihud Illiquidity Ratio",
        "Order Book Imbalance (OBI) Indicator",
        "Spread Cost Estimation Model",
    ],
}


def _mean(xs: List[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def _stdev(xs: List[float]) -> float:
    return statistics.stdev(xs) if len(xs) > 1 else 0.0


def _safe(v: float, digits: int = 6) -> float:
    return round(float(v), digits) if math.isfinite(float(v)) else 0.0


def _log_returns(closes: List[float]) -> List[float]:
    return [math.log(b / a) for a, b in zip(closes[:-1], closes[1:]) if a > 0 and b > 0]


def _ols_ar1(xs: List[float]) -> Dict[str, float]:
    if len(xs) < 8:
        return {"alpha": 0.0, "beta": 0.0, "resid_std": 0.0}
    x, y = xs[:-1], xs[1:]
    xm, ym = _mean(x), _mean(y)
    den = sum((v - xm) ** 2 for v in x)
    beta = 0.0 if den == 0 else sum((x[i] - xm) * (y[i] - ym) for i in range(len(x))) / den
    alpha = ym - beta * xm
    resid = [y[i] - alpha - beta * x[i] for i in range(len(x))]
    return {"alpha": alpha, "beta": beta, "resid_std": _stdev(resid)}


def _hurst(closes: List[float]) -> Optional[float]:
    if len(closes) < 40:
        return None
    lags, tau = [], []
    for lag in range(2, min(20, len(closes) // 3)):
        diffs = [closes[i] - closes[i - lag] for i in range(lag, len(closes))]
        s = _stdev(diffs)
        if s > 0:
            lags.append(math.log(lag)); tau.append(math.log(s))
    if len(lags) < 3:
        return None
    xm, ym = _mean(lags), _mean(tau)
    den = sum((x - xm) ** 2 for x in lags)
    return None if den == 0 else sum((lags[i] - xm) * (tau[i] - ym) for i in range(len(lags))) / den


def _vol_estimators(bars: List[dict]) -> Dict[str, float]:
    n = len(bars)
    if n < 3:
        return {}
    par = []
    gk = []
    yz_rs = []
    oc = []
    oo = []
    prev_c = None
    for b in bars:
        o, h, l, c = map(float, (b["open"], b["high"], b["low"], b["close"]))
        if min(o, h, l, c) <= 0:
            continue
        hl = math.log(h / l)
        co = math.log(c / o)
        par.append((hl * hl) / (4.0 * math.log(2.0)))
        gk.append(0.5 * hl * hl - (2.0 * math.log(2.0) - 1.0) * co * co)
        yz_rs.append(math.log(h / c) * math.log(h / o) + math.log(l / c) * math.log(l / o))
        oc.append(co)
        if prev_c and prev_c > 0:
            oo.append(math.log(o / prev_c))
        prev_c = c
    if not par:
        return {}
    k = 0.34 / (1.34 + (len(par) + 1) / max(1, len(par) - 1))
    yz = (_stdev(oo) ** 2 if len(oo) > 1 else 0.0) + k * (_stdev(oc) ** 2 if len(oc) > 1 else 0.0) + (1 - k) * max(0.0, _mean(yz_rs))
    return {
        "parkinson": math.sqrt(max(0.0, _mean(par))),
        "garman_klass": math.sqrt(max(0.0, _mean(gk))),
        "yang_zhang": math.sqrt(max(0.0, yz)),
    }


def _garch_proxy(rets: List[float]) -> Dict[str, float]:
    if len(rets) < 20:
        return {}
    omega, alpha, beta = 1e-8, 0.08, 0.90
    var = max(_stdev(rets) ** 2, 1e-12)
    for r in rets[-120:]:
        var = omega + alpha * r * r + beta * var
    last = rets[-1]
    leverage = 0.12 * last * last if last < 0 else 0.0
    egarch_like = max(1e-12, var + leverage)
    tgarch_like = max(1e-12, var + (0.18 * last * last if last < 0 else 0.0))
    return {"garch_sigma": math.sqrt(var), "egarch_sigma_proxy": math.sqrt(egarch_like), "tgarch_sigma_proxy": math.sqrt(tgarch_like)}


def _kalman(closes: List[float]) -> Dict[str, float]:
    if len(closes) < 5:
        return {}
    x = closes[0]
    p, q, r = 1.0, 1e-4, max((_stdev(closes[-30:]) or 1e-6) ** 2, 1e-9)
    for z in closes[1:]:
        p += q
        k = p / (p + r)
        x = x + k * (z - x)
        p = (1 - k) * p
    innovation = closes[-1] - x
    return {"state": x, "innovation": innovation, "innovation_pct": innovation / max(abs(x), 1e-12)}


def _holt(closes: List[float], alpha: float = 0.35, beta: float = 0.12) -> Dict[str, float]:
    if len(closes) < 3:
        return {}
    level, trend = closes[0], closes[1] - closes[0]
    for z in closes[1:]:
        old = level
        level = alpha * z + (1 - alpha) * (level + trend)
        trend = beta * (level - old) + (1 - beta) * trend
    return {"level": level, "trend": trend, "forecast_1": level + trend}


def _fft_cycle(rets: List[float]) -> Dict[str, float]:
    xs = rets[-64:]
    n = len(xs)
    if n < 16:
        return {}
    xm = _mean(xs)
    best_k, best_amp = 0, 0.0
    for k in range(1, max(2, n // 2)):
        re = sum((xs[t] - xm) * math.cos(2 * math.pi * k * t / n) for t in range(n))
        im = -sum((xs[t] - xm) * math.sin(2 * math.pi * k * t / n) for t in range(n))
        amp = math.hypot(re, im)
        if amp > best_amp:
            best_k, best_amp = k, amp
    return {"dominant_period_bars": (n / best_k) if best_k else 0.0, "amplitude": best_amp / max(1, n)}


def _microstructure(bars: List[dict]) -> Dict[str, object]:
    xs = bars[-80:]
    vols = [max(0.0, float(b.get("volume", 0.0))) for b in xs]
    closes = [float(b["close"]) for b in xs]
    typical = [(float(b["high"]) + float(b["low"]) + float(b["close"])) / 3.0 for b in xs]
    tot = sum(vols)
    vwap = sum(typical[i] * vols[i] for i in range(len(xs))) / tot if tot > 0 else None
    twap = _mean(typical) if typical else None
    rets = [abs(math.log(b / a)) for a, b in zip(closes[:-1], closes[1:]) if a > 0 and b > 0]
    dollar_vol = [max(1e-12, closes[i] * vols[i]) for i in range(min(len(rets), len(vols)))]
    amihud = _mean([rets[i] / dollar_vol[i] for i in range(min(len(rets), len(dollar_vol)))]) if rets else None
    spreads = [(float(b["high"]) - float(b["low"])) / max(float(b["close"]), 1e-12) for b in xs]
    spread_proxy = _mean(spreads[-20:]) if spreads else None
    bid = bars[-1].get("bid_size") if bars else None
    ask = bars[-1].get("ask_size") if bars else None
    obi = None
    if bid is not None and ask is not None and float(bid) + float(ask) > 0:
        obi = (float(bid) - float(ask)) / (float(bid) + float(ask))
    return {"vwap": vwap, "twap": twap, "amihud": amihud, "spread_cost_proxy": spread_proxy, "obi": obi}


def _parity(macro: Dict[str, float], spot: float) -> Dict[str, object]:
    rd = macro.get("domestic_rate")
    rf = macro.get("foreign_rate")
    t = float(macro.get("tenor_years", 1.0))
    out: Dict[str, object] = {}
    if rd is not None and rf is not None and spot > 0:
        rd, rf = float(rd), float(rf)
        out["cirp_forward"] = spot * (1 + rd * t) / max(1e-12, (1 + rf * t))
        out["uirp_expected_spot"] = spot * (1 + (rd - rf) * t)
    dom_inf, for_inf = macro.get("domestic_inflation"), macro.get("foreign_inflation")
    if dom_inf is not None and for_inf is not None and spot > 0:
        out["ppp_expected_spot"] = spot * (1 + float(dom_inf) * t) / max(1e-12, (1 + float(for_inf) * t))
    if rd is not None and rf is not None and dom_inf is not None and for_inf is not None:
        out["rird"] = (float(rd) - float(dom_inf)) - (float(rf) - float(for_inf))
    tri = macro.get("triangular_rates")
    if isinstance(tri, dict) and all(k in tri for k in ("ab", "bc", "ac")):
        implied = float(tri["ab"]) * float(tri["bc"])
        out["triangular_arbitrage_gap"] = implied / max(float(tri["ac"]), 1e-12) - 1.0
    if macro.get("xccy_basis_bps") is not None:
        out["cross_currency_basis_bps"] = float(macro["xccy_basis_bps"])
    return out


def evaluate_model_library(bars: List[dict], macro: Optional[Dict[str, float]] = None) -> dict:
    macro = macro or {}
    closes = [float(b["close"]) for b in bars]
    rets = _log_returns(closes)
    vols = _vol_estimators(bars[-120:])
    garch = _garch_proxy(rets)
    ar1 = _ols_ar1(closes[-120:])
    beta = ar1.get("beta", 0.0)
    half_life = (-math.log(2.0) / math.log(abs(beta))) if 0 < abs(beta) < 1 else None
    mu = ar1.get("alpha", 0.0) / max(1e-12, 1.0 - beta) if abs(beta) < 0.999 else None
    sd = _stdev(closes[-60:])
    z = (closes[-1] - _mean(closes[-60:])) / sd if closes and sd > 0 else 0.0
    h = _hurst(closes[-160:])
    kal = _kalman(closes[-160:])
    holt = _holt(closes[-160:])
    fft = _fft_cycle(rets)
    micro = _microstructure(bars)
    parity = _parity(macro, closes[-1] if closes else 0.0)

    active = {
        "valuation_parity_arbitrage": parity,
        "stochastic_options_volatility": {
            "gbm_drift": _mean(rets[-60:]) if rets else 0.0,
            "gbm_sigma": _stdev(rets[-60:]) if len(rets) > 1 else 0.0,
            **vols,
            **garch,
        },
        "stat_arb_mean_reversion_econometrics": {
            "z_score": z,
            "ou_theta_proxy": (1.0 - beta) if beta < 1 else 0.0,
            "ou_mean_proxy": mu,
            "half_life_bars": half_life,
            "hurst_exponent": h,
            "adf_proxy_ar1_beta": beta,
        },
        "signal_processing_time_series_ml": {**kal, **holt, **fft},
        "execution_microstructure_hft": micro,
    }

    unavailable = {
        "Black-Scholes Model (Forex Garman-Kohlhagen Extension)": "needs strike, expiry, domestic/foreign rates and option price/IV inputs",
        "Heston Stochastic Volatility Model": "needs option surface/calibration inputs",
        "SABR Volatility Model": "needs strikes/forwards/IV surface for calibration",
        "Implied Volatility Surface Interpolation (SVI / Cubic Spline)": "needs implied-volatility smile/surface data",
        "Johansen Cointegration Test": "needs multiple synchronized price series",
        "Engle-Granger Two-Step Cointegration Test": "needs a second synchronized series",
        "Vector Autoregression (VAR) Model": "needs multivariate synchronized series",
        "Error Correction Model (ECM)": "needs cointegrated multivariate series",
        "SARIMAX (Seasonal ARIMA with Exogenous Variables)": "needs explicit exogenous series and seasonal configuration",
        "Extended / Unscented Kalman Filter": "needs nonlinear state/measurement model specification",
        "Wavelet Transform": "not activated without a wavelet basis/configuration",
        "Hidden Markov Model (HMM)": "needs fitted state-transition/emission parameters",
        "Principal Component Analysis (PCA)": "needs a multivariate return matrix",
        "Almgren-Chriss Optimal Execution Model": "needs order size, horizon, risk aversion and impact calibration",
        "Kyle’s Lambda (Market Impact Estimator)": "needs signed trade flow / higher-quality transaction data",
        "Order Book Imbalance (OBI) Indicator": "needs real bid/ask depth; returns only when bid_size/ask_size are provided",
    }

    flat_values = []
    for group in active.values():
        for value in group.values():
            if isinstance(value, (int, float)) and math.isfinite(value):
                flat_values.append(abs(float(value)))

    return {
        "catalog": MODEL_LIBRARY,
        "active_outputs": _round_nested(active),
        "unavailable_or_input_gated": unavailable,
        "active_model_groups": sum(1 for g in active.values() if g),
        "integrity": "Models run only when their required inputs exist. Missing option, depth, cross-asset or exogenous inputs are never fabricated.",
    }


def _round_nested(obj):
    if isinstance(obj, dict):
        return {k: _round_nested(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_nested(v) for v in obj]
    if isinstance(obj, float):
        return _safe(obj)
    return obj
