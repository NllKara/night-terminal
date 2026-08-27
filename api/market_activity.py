from __future__ import annotations

import json
import urllib.parse
import urllib.request


def _get_json(url: str, headers: dict | None = None, timeout: int = 10):
    req = urllib.request.Request(url, headers=headers or {"User-Agent":"NIGHT-Terminal/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def oil_snapshot() -> dict:
    """Keyless futures snapshot via Yahoo as a resilient free default."""
    out={}
    for name,ticker in {"WTI":"CL=F","BRENT":"BZ=F","NATGAS":"NG=F"}.items():
        try:
            q=_get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?interval=5m&range=1d")
            r=(q.get("chart",{}).get("result") or [None])[0]
            meta=(r or {}).get("meta",{})
            out[name]={
                "price": meta.get("regularMarketPrice"),
                "previous_close": meta.get("chartPreviousClose"),
                "currency": meta.get("currency","USD"),
                "exchange": meta.get("exchangeName"),
                "source":"Yahoo futures (unofficial/free)"
            }
        except Exception:
            out[name]={"price":None,"source":"unavailable"}
    return out


def shipping_snapshot(limit: int = 80) -> dict:
    """Anonymous AIS snapshot from Open Waters. Coverage depends on contributing stations."""
    try:
        data=_get_json("https://ais.openwaters.io/v1/vessels")
        features=data.get("features",[]) if isinstance(data,dict) else []
        vessels=[]
        for f in features[:limit]:
            p=f.get("properties",{}) or {}; g=f.get("geometry",{}) or {}
            coords=g.get("coordinates") or [None,None]
            vessels.append({
                "mmsi":p.get("mmsi"),"name":p.get("name") or p.get("shipName"),
                "lat":coords[1] if len(coords)>1 else None,"lon":coords[0] if coords else None,
                "speed":p.get("sog") or p.get("speed"),"course":p.get("cog") or p.get("course"),
                "status":p.get("navigationStatus") or p.get("status"),"destination":p.get("destination")
            })
        return {"source":"Open Waters AIS","count":len(features),"vessels":vessels}
    except Exception as e:
        return {"source":"Open Waters AIS","count":0,"vessels":[],"error":type(e).__name__}


def activity_snapshot() -> dict:
    return {"oil":oil_snapshot(),"shipping":shipping_snapshot()}
