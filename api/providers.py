from __future__ import annotations

import json
import math
import os
import statistics
import urllib.parse
import urllib.request


def _get_json(url: str, headers: dict | None = None, timeout: int = 12):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0 NIGHT-Terminal/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _mean(xs): return statistics.fmean(xs) if xs else 0.0
def _stdev(xs): return statistics.stdev(xs) if len(xs) > 1 else 0.0
def _z_last_change(xs):
    if len(xs) < 5: return 0.0
    d=[b-a for a,b in zip(xs[:-1],xs[1:])]
    s=_stdev(d[:-1])
    return 0.0 if s==0 else (d[-1]-_mean(d[:-1]))/s

def _squash(x,scale=2.0): return math.tanh(x/scale)

def _interval_map(tf: str) -> str:
    return {"1m":"1min","5m":"5min","15m":"15min","1h":"1h","4h":"4h","1D":"1day","1d":"1day"}.get(tf,"5min")

def _oanda_granularity(tf: str) -> str:
    return {"1m":"M1","5m":"M5","15m":"M15","1h":"H1","4h":"H4","1D":"D","1d":"D"}.get(tf,"M5")

def _symbol_td(symbol: str) -> str:
    return {"XAUUSD":"XAU/USD","EURUSD":"EUR/USD","GBPUSD":"GBP/USD","USDJPY":"USD/JPY","BTCUSD":"BTC/USD"}.get(symbol.upper(),symbol.upper())

def _symbol_oanda(symbol: str) -> str:
    return {"XAUUSD":"XAU_USD","EURUSD":"EUR_USD","GBPUSD":"GBP_USD","USDJPY":"USD_JPY"}.get(symbol.upper(),symbol.upper())

def _binance_symbol(symbol: str) -> str | None:
    return {"BTCUSD":"BTCUSDT"}.get(symbol.upper())


def _yahoo_gc(timeframe: str) -> dict:
    # Keyless COMEX Gold futures proxy. Yahoo's chart endpoint is unofficial and GC=F is delayed,
    # but candle volume is exchange-traded futures volume rather than CFD/spot tick volume.
    interval={"1m":"1m","5m":"5m","15m":"15m","1h":"60m","4h":"60m","1D":"1d","1d":"1d"}.get(timeframe,"5m")
    range_={"1m":"5d","5m":"5d","15m":"5d","1h":"1mo","4h":"1mo","1D":"6mo","1d":"6mo"}.get(timeframe,"5d")
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval={interval}&range={range_}&includePrePost=true"
    data=_get_json(url)
    result=(data.get("chart",{}).get("result") or [None])[0]
    if not result: raise RuntimeError("Yahoo GC chart unavailable")
    ts=result.get("timestamp") or []
    q=((result.get("indicators",{}).get("quote") or [{}])[0])
    bars=[]
    for i,t in enumerate(ts):
        try:
            o=q["open"][i]; h=q["high"][i]; l=q["low"][i]; c=q["close"][i]; v=q["volume"][i]
            if None in (o,h,l,c): continue
            bars.append({"time":t,"open":float(o),"high":float(h),"low":float(l),"close":float(c),"volume":float(v or 0)})
        except (IndexError,KeyError,TypeError,ValueError):
            continue
    # Build true 4H bars from 1H futures candles.
    if timeframe=="4h" and bars:
        grouped=[]
        for i in range(0,len(bars),4):
            x=bars[i:i+4]
            if len(x)<4: continue
            grouped.append({"time":x[0]["time"],"open":x[0]["open"],"high":max(b["high"] for b in x),"low":min(b["low"] for b in x),"close":x[-1]["close"],"volume":sum(b["volume"] for b in x)})
        bars=grouped
    return {"bars":bars[-180:],"source":"COMEX Gold futures GC=F via Yahoo Finance (unofficial/delayed)","volume_type":"exchange-traded COMEX futures volume proxy for XAUUSD","freshness":0.72,"is_proxy":True}


class MarketProvider:
    async def snapshot(self, symbol: str, timeframe: str, credentials: dict | None = None) -> dict:
        credentials = credentials or {}; errors=[]

        # OANDA remains optional. If present, it gives XAU/FX spot-style candles and tick volume.
        token=credentials.get("oanda_token") or os.environ.get("OANDA_TOKEN")
        if token and symbol.upper() in {"XAUUSD","EURUSD","GBPUSD","USDJPY"}:
            try:
                inst=_symbol_oanda(symbol)
                params=urllib.parse.urlencode({"granularity":_oanda_granularity(timeframe),"count":180,"price":"M"})
                data=_get_json(f"https://api-fxpractice.oanda.com/v3/instruments/{inst}/candles?{params}",{"Authorization":f"Bearer {token}","User-Agent":"NIGHT-Terminal/1.0"})
                bars=[]
                for c in data.get("candles",[]):
                    m=c.get("mid") or {}
                    if m: bars.append({"time":c.get("time"),"open":float(m["o"]),"high":float(m["h"]),"low":float(m["l"]),"close":float(m["c"]),"volume":float(c.get("volume",0))})
                if len(bars)>=30:return {"bars":bars,"source":"OANDA practice v20","volume_type":"tick volume (price-update count)","freshness":1.0,"is_proxy":False}
            except Exception as e: errors.append(f"OANDA: {type(e).__name__}")

        # XAUUSD zero-key fallback: quantify COMEX GC futures instead of fabricating spot volume.
        if symbol.upper()=="XAUUSD":
            try:
                gc=_yahoo_gc(timeframe)
                if len(gc["bars"])>=30:
                    gc["provider_errors"]=errors
                    return gc
                errors.append("GC futures returned too few candles")
            except Exception as e: errors.append(f"GC futures proxy: {type(e).__name__}")

        bsym=_binance_symbol(symbol)
        if bsym:
            try:
                interval={"1m":"1m","5m":"5m","15m":"15m","1h":"1h","4h":"4h","1D":"1d","1d":"1d"}.get(timeframe,"5m")
                rows=_get_json(f"https://api.binance.com/api/v3/klines?symbol={bsym}&interval={interval}&limit=180")
                bars=[{"time":r[0],"open":float(r[1]),"high":float(r[2]),"low":float(r[3]),"close":float(r[4]),"volume":float(r[5])} for r in rows]
                if len(bars)>=30:return {"bars":bars,"source":"Binance public market data","volume_type":"exchange-traded base-asset volume","freshness":1.0,"is_proxy":False}
            except Exception as e: errors.append(f"Binance: {type(e).__name__}")

        td_key=credentials.get("twelve_key") or os.environ.get("TWELVE_DATA_API_KEY")
        if td_key:
            try:
                params=urllib.parse.urlencode({"symbol":_symbol_td(symbol),"interval":_interval_map(timeframe),"outputsize":180,"apikey":td_key,"format":"JSON"})
                data=_get_json(f"https://api.twelvedata.com/time_series?{params}")
                if data.get("status")=="error":raise RuntimeError(data.get("message","Twelve Data error"))
                bars=[]
                for r in reversed(data.get("values",[])):
                    bars.append({"time":r.get("datetime"),"open":float(r["open"]),"high":float(r["high"]),"low":float(r["low"]),"close":float(r["close"]),"volume":float(r.get("volume") or 0)})
                if len(bars)>=30:
                    vt="provider volume" if sum(b["volume"] for b in bars[-20:])>0 else "unavailable for this feed"
                    return {"bars":bars,"source":"Twelve Data Basic/REST","volume_type":vt,"freshness":0.95,"is_proxy":False}
            except Exception as e: errors.append(f"Twelve Data: {type(e).__name__}")
        return {"bars":[],"source":"none","volume_type":"none","freshness":0.0,"provider_errors":errors,"is_proxy":False}


class MacroProvider:
    def _fred_series(self, series_id: str, key: str, limit: int = 40):
        params=urllib.parse.urlencode({"series_id":series_id,"api_key":key,"file_type":"json","sort_order":"desc","limit":limit})
        data=_get_json(f"https://api.stlouisfed.org/fred/series/observations?{params}")
        vals=[]
        for r in reversed(data.get("observations",[])):
            try: vals.append(float(r["value"]))
            except: pass
        return vals

    async def snapshot(self, symbol: str, credentials: dict | None = None) -> dict:
        credentials=credentials or {}
        key=credentials.get("fred_key") or os.environ.get("FRED_API_KEY")
        if not key:return {"macro_score":0.0,"intermarket_score":0.0,"freshness":0.7,"macro_source":"neutral: FRED key not configured"}
        try:
            y10=self._fred_series("DGS10",key); real10=self._fred_series("DFII10",key); y2=self._fred_series("DGS2",key); unrate=self._fred_series("UNRATE",key,24); cpi=self._fred_series("CPIAUCSL",key,36)
            z10=_z_last_change(y10); zr=_z_last_change(real10); z2=_z_last_change(y2); zu=_z_last_change(unrate)
            yoy=[(cpi[i]/cpi[i-12]-1)*100 for i in range(12,len(cpi)) if cpi[i-12]!=0]
            zc=_z_last_change(yoy)
            gold_impulse=(-0.34*_squash(zr)-0.22*_squash(z10)-0.16*_squash(z2)+0.18*_squash(zu)+0.10*_squash(zc))
            sym=symbol.upper()
            if sym=="XAUUSD":score=gold_impulse
            elif sym in {"EURUSD","GBPUSD"}:score=-gold_impulse*0.55
            elif sym=="USDJPY":score=gold_impulse*0.45
            else:score=0.0
            return {"macro_score":max(-1,min(1,score)),"intermarket_score":max(-1,min(1,-0.45*_squash(zr)-0.25*_squash(z10)-0.15*_squash(z2))),"freshness":0.9,"macro_source":"FRED official","macro_details":{"DGS10_change_z":round(z10,3),"DFII10_change_z":round(zr,3),"DGS2_change_z":round(z2,3),"UNRATE_change_z":round(zu,3),"CPI_yoy_change_z":round(zc,3)}}
        except Exception as e:
            return {"macro_score":0.0,"intermarket_score":0.0,"freshness":0.5,"macro_source":f"FRED error: {type(e).__name__}"}

    async def calendar(self) -> list:
        return [{"time":None,"currency":"USD","event":"TradingView calendar widget available in frontend; structured surprise API connector pending","impact":"INFO","forecast":"—","previous":"—"}]
