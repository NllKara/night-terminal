from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def _get_json(url: str, timeout: int = 12):
    req = urllib.request.Request(url, headers={"User-Agent": "NIGHT-Terminal/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _news_query(symbol: str) -> str:
    s = symbol.upper()
    if s == "XAUUSD":
        return '(gold OR bullion OR "gold futures" OR XAUUSD OR "Federal Reserve" OR "Treasury yields" OR dollar)'
    if s == "BTCUSD":
        return '(bitcoin OR BTC OR crypto OR cryptocurrency OR "Federal Reserve" OR dollar)'
    if s in {"EURUSD", "GBPUSD", "USDJPY"}:
        return f'({s} OR forex OR "Federal Reserve" OR dollar OR yields)'
    return f'({s} OR markets OR futures OR "Federal Reserve")'


def _headline_score(title: str, symbol: str) -> float:
    t = title.lower()
    bullish_gold = ["weaker dollar", "dollar falls", "yields fall", "yield falls", "rate cut", "dovish", "safe haven", "geopolitical tensions", "debasement", "gold rises", "gold gains", "inflation fears"]
    bearish_gold = ["stronger dollar", "dollar rises", "yields rise", "yield rises", "rate hike", "hawkish", "gold falls", "gold drops", "risk appetite", "ceasefire"]
    pos = sum(1 for k in bullish_gold if k in t)
    neg = sum(1 for k in bearish_gold if k in t)
    raw = pos - neg
    if symbol.upper() != "XAUUSD":
        generic_pos = ["rises", "gains", "surges", "beats", "strong demand", "eases inflation"]
        generic_neg = ["falls", "drops", "slumps", "misses", "weak demand", "inflation accelerates"]
        raw = sum(1 for k in generic_pos if k in t) - sum(1 for k in generic_neg if k in t)
    return math.tanh(raw / 2.0)


def fetch_news(symbol: str, max_records: int = 20) -> dict:
    try:
        params = urllib.parse.urlencode({
            "query": _news_query(symbol),
            "mode": "ArtList",
            "maxrecords": max_records,
            "format": "json",
            "sort": "HybridRel",
        })
        data = _get_json(f"https://api.gdeltproject.org/api/v2/doc/doc?{params}")
        rows = []
        scores = []
        for a in data.get("articles", [])[:max_records]:
            title = (a.get("title") or "").strip()
            if not title:
                continue
            sc = _headline_score(title, symbol)
            scores.append(sc)
            rows.append({
                "title": title,
                "url": a.get("url"),
                "domain": a.get("domain"),
                "seen": a.get("seendate"),
                "language": a.get("language"),
                "country": a.get("sourcecountry"),
                "sentiment": round(sc, 3),
            })
        score = sum(scores) / len(scores) if scores else 0.0
        return {
            "source": "GDELT DOC 2.0",
            "score": round(_clamp(score), 4),
            "count": len(rows),
            "articles": rows,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"source": "GDELT DOC 2.0", "score": 0.0, "count": 0, "articles": [], "error": type(e).__name__}


def fetch_cot_gold(limit: int = 52) -> dict:
    try:
        where = "upper(market_and_exchange_names) like '%GOLD%'"
        params = urllib.parse.urlencode({
            "$limit": limit,
            "$where": where,
            "$order": "report_date_as_yyyy_mm_dd DESC",
        })
        rows = _get_json(f"https://publicreporting.cftc.gov/resource/72hh-3qpy.json?{params}")
        parsed = []
        for r in rows:
            try:
                long_v = float(r.get("m_money_positions_long_all", 0) or 0)
                short_v = float(r.get("m_money_positions_short_all", 0) or 0)
                oi = float(r.get("open_interest_all", 0) or 0)
                net = long_v - short_v
                norm = net / oi if oi else 0.0
                parsed.append({
                    "date": r.get("report_date_as_yyyy_mm_dd"),
                    "market": r.get("market_and_exchange_names"),
                    "managed_money_long": long_v,
                    "managed_money_short": short_v,
                    "managed_money_net": net,
                    "open_interest": oi,
                    "net_pct_oi": norm,
                })
            except Exception:
                continue
        if not parsed:
            return {"source": "CFTC PRE", "score": 0.0, "rows": []}
        hist = [x["net_pct_oi"] for x in parsed]
        latest = hist[0]
        mu = sum(hist) / len(hist)
        sd = (sum((x - mu) ** 2 for x in hist) / max(1, len(hist) - 1)) ** 0.5
        z = 0.0 if sd == 0 else (latest - mu) / sd
        score = math.tanh(z / 2.0)
        return {
            "source": "CFTC Disaggregated Futures Only",
            "score": round(_clamp(score), 4),
            "zscore": round(z, 3),
            "latest": parsed[0],
            "rows": parsed,
        }
    except Exception as e:
        return {"source": "CFTC PRE", "score": 0.0, "rows": [], "error": type(e).__name__}


def intelligence_snapshot(symbol: str) -> dict:
    news = fetch_news(symbol)
    cot = fetch_cot_gold() if symbol.upper() == "XAUUSD" else {"source": "CFTC PRE", "score": 0.0, "rows": []}
    return {"news": news, "cot": cot}
