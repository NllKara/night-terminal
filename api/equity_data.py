from __future__ import annotations

import json, os, time, urllib.parse, urllib.request

US = {"AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","JPM","V","MA","LLY","WMT","XOM","COST","NFLX","AMD","CRM","ORCL","PLTR"}
ID = {"BBCA","BBRI","BMRI","BBNI","TLKM","ASII","AMMN","DSSA","BYAN","GOTO","ADRO","ANTM","INCO","MDKA","ICBP","INDF","UNVR","KLBF","PGAS","CPIN"}
IDX = {"SPX":"^GSPC","NDX":"^NDX","DJI":"^DJI","RUT":"^RUT","IHSG":"^JKSE","LQ45":"^JKLQ45"}

SEC_TAGS={
 "revenue":["RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","SalesRevenueNet"],
 "net_income":["NetIncomeLoss","ProfitLoss"],
 "assets":["Assets"],
 "liabilities":["Liabilities"],
 "equity":["StockholdersEquity"],
 "operating_income":["OperatingIncomeLoss"],
 "operating_cash_flow":["NetCashProvidedByUsedInOperatingActivities"],
 "eps_diluted":["EarningsPerShareDiluted"],
 "shares":["CommonStockSharesOutstanding"]
}

_ticker_map=None

def _json(url, headers=None, timeout=12):
    req=urllib.request.Request(url,headers=headers or {"User-Agent":"NIGHT Terminal research contact: market-data@night.local"})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode("utf-8"))

def _td_symbol(symbol):
    s=symbol.upper()
    if s in ID:return s,{"mic_code":"XIDX"}
    return s,{}

def _td_get(endpoint,symbol,key,extra=None):
    sym,filters=_td_symbol(symbol)
    q={"symbol":sym,"apikey":key,**filters,**(extra or {})}
    return _json("https://api.twelvedata.com/"+endpoint+"?"+urllib.parse.urlencode(q))

def _yahoo_symbol(symbol):
    s=symbol.upper()
    if s in ID:return s+".JK"
    return IDX.get(s,s)

def _yahoo_chart(symbol,interval="5m",range_="5d"):
    ys=urllib.parse.quote(_yahoo_symbol(symbol),safe="")
    d=_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{ys}?interval={interval}&range={range_}&includePrePost=true")
    r=(d.get("chart",{}).get("result") or [None])[0]
    if not r:return {"bars":[],"meta":{}}
    ts=r.get("timestamp") or []; q=((r.get("indicators",{}).get("quote") or [{}])[0]); bars=[]
    for i,t in enumerate(ts):
        try:
            o,h,l,c=q["open"][i],q["high"][i],q["low"][i],q["close"][i];v=(q.get("volume") or [0]*len(ts))[i]
            if None in (o,h,l,c):continue
            bars.append({"time":t*1000,"open":float(o),"high":float(h),"low":float(l),"close":float(c),"volume":float(v or 0)})
        except Exception:pass
    return {"bars":bars,"meta":r.get("meta") or {}}

def _yahoo_quote(symbol):
    ys=urllib.parse.quote(_yahoo_symbol(symbol),safe="")
    try:
        d=_json(f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={ys}")
        return ((d.get("quoteResponse",{}).get("result") or [{}])[0])
    except Exception:return {}

def _sec_tickers():
    global _ticker_map
    if _ticker_map is None:
        d=_json("https://www.sec.gov/files/company_tickers.json",{"User-Agent":"NIGHT Terminal market-data@night.local"})
        _ticker_map={v.get("ticker","").upper():str(v.get("cik_str","")).zfill(10) for v in d.values()}
    return _ticker_map

def _latest_fact(facts,tags):
    gaap=(facts.get("facts") or {}).get("us-gaap") or {}
    for tag in tags:
        node=gaap.get(tag) or {}
        units=node.get("units") or {}
        for unit in ("USD","USD/shares","shares"):
            vals=units.get(unit) or []
            if vals:
                vals=sorted(vals,key=lambda x:(x.get("filed") or "",x.get("end") or ""),reverse=True)
                for x in vals:
                    if x.get("val") is not None:return {"value":x.get("val"),"unit":unit,"end":x.get("end"),"filed":x.get("filed"),"form":x.get("form")}
    return None

def sec_fundamentals(symbol):
    s=symbol.upper()
    if s not in US:return {"available":False,"source":"SEC not applicable"}
    try:
        cik=_sec_tickers().get(s)
        if not cik:return {"available":False,"source":"SEC","error":"CIK not found"}
        d=_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",{"User-Agent":"NIGHT Terminal market-data@night.local"})
        out={k:_latest_fact(d,tags) for k,tags in SEC_TAGS.items()}
        return {"available":True,"source":"SEC EDGAR XBRL","company":d.get("entityName"),"cik":cik,"facts":out}
    except Exception as e:return {"available":False,"source":"SEC EDGAR XBRL","error":type(e).__name__}

def td_fundamentals(symbol,key):
    if not key:return {"available":False,"source":"Twelve Data","error":"API key not configured"}
    try:
        stats=_td_get("statistics",symbol,key)
        profile=_td_get("profile",symbol,key)
        if stats.get("status")=="error":return {"available":False,"source":"Twelve Data","error":stats.get("message")}
        return {"available":True,"source":"Twelve Data fundamentals","statistics":stats,"profile":profile}
    except Exception as e:return {"available":False,"source":"Twelve Data fundamentals","error":type(e).__name__}

def equity_snapshot(symbol,key=None):
    s=symbol.upper(); key=key or os.getenv("TWELVE_DATA_API_KEY")
    price=None; price_source="none"; freshness="NO DATA"; bars=[]; meta={}; errors=[]
    if key:
        try:
            p=_td_get("price",s,key)
            if p.get("price") is not None:
                price=float(p["price"]); price_source="Twelve Data latest price"; freshness="LIVE/PLAN-DEPENDENT"
            interval="5min"
            ts=_td_get("time_series",s,key,{"interval":interval,"outputsize":180,"format":"JSON"})
            if ts.get("status")!="error":
                for r in reversed(ts.get("values") or []):
                    bars.append({"time":r.get("datetime"),"open":float(r["open"]),"high":float(r["high"]),"low":float(r["low"]),"close":float(r["close"]),"volume":float(r.get("volume") or 0)})
        except Exception as e:errors.append("Twelve Data "+type(e).__name__)
    if price is None or len(bars)<30:
        try:
            y=_yahoo_chart(s); meta=y["meta"]
            if len(bars)<30:bars=y["bars"]
            if price is None:
                price=float(meta.get("regularMarketPrice") or (bars[-1]["close"] if bars else 0)) or None
                price_source="Yahoo Finance fallback (unofficial)"
                freshness="DELAYED/EXCHANGE-DEPENDENT"
        except Exception as e:errors.append("Yahoo "+type(e).__name__)
    quote=_yahoo_quote(s)
    fundamentals=td_fundamentals(s,key)
    sec=sec_fundamentals(s)
    return {"symbol":s,"price":price,"price_source":price_source,"freshness":freshness,"bars":bars[-180:],"quote":quote,"fundamentals":fundamentals,"sec":sec,"errors":errors,"updated_at":int(time.time())}
