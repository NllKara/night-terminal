from __future__ import annotations

import json, math, os, statistics, urllib.parse, urllib.request


def _get_json(url: str, headers: dict | None = None, timeout: int = 12):
    req=urllib.request.Request(url,headers=headers or {"User-Agent":"Mozilla/5.0 NIGHT-Terminal/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode("utf-8"))

def _mean(xs):return statistics.fmean(xs) if xs else 0.0
def _stdev(xs):return statistics.stdev(xs) if len(xs)>1 else 0.0
def _z_last_change(xs):
    if len(xs)<5:return 0.0
    d=[b-a for a,b in zip(xs[:-1],xs[1:])];s=_stdev(d[:-1]);return 0.0 if s==0 else (d[-1]-_mean(d[:-1]))/s
def _squash(x,scale=2.0):return math.tanh(x/scale)
def _interval_map(tf):return {"1m":"1min","5m":"5min","15m":"15min","1h":"1h","4h":"4h","1D":"1day","1d":"1day"}.get(tf,"5min")
def _oanda_granularity(tf):return {"1m":"M1","5m":"M5","15m":"M15","1h":"H1","4h":"H4","1D":"D","1d":"D"}.get(tf,"M5")

def _is_fx_pair(symbol:str)->bool:
    s=symbol.upper().replace("/","")
    return len(s)==6 and s.isalpha() and s not in {"NAS100"}

def _symbol_td(symbol:str)->str:
    s=symbol.upper().replace("/","")
    fixed={"XAUUSD":"XAU/USD","XAGUSD":"XAG/USD","BTCUSD":"BTC/USD","ETHUSD":"ETH/USD","NAS100":"NDX","US30":"DJI","SPX500":"SPX"}
    if s in fixed:return fixed[s]
    if _is_fx_pair(s):return f"{s[:3]}/{s[3:]}"
    return s

def _symbol_oanda(symbol:str)->str:
    s=symbol.upper().replace("/","")
    if s in {"XAUUSD","XAGUSD"}:return f"{s[:3]}_{s[3:]}"
    if _is_fx_pair(s):return f"{s[:3]}_{s[3:]}"
    return s

def _binance_symbol(symbol):return {"BTCUSD":"BTCUSDT","ETHUSD":"ETHUSDT"}.get(symbol.upper())

class MarketProvider:
    async def snapshot(self,symbol:str,timeframe:str,credentials:dict|None=None)->dict:
        credentials=credentials or {};errors=[];sym=symbol.upper().replace("/","")
        td_key=credentials.get("twelve_key") or os.environ.get("TWELVE_DATA_API_KEY")
        # Price-first primary source: exact same FX/metal/index/crypto instrument through Twelve Data.
        if td_key:
            try:
                params=urllib.parse.urlencode({"symbol":_symbol_td(sym),"interval":_interval_map(timeframe),"outputsize":240,"apikey":td_key,"format":"JSON"})
                data=_get_json(f"https://api.twelvedata.com/time_series?{params}")
                if data.get("status")=="error":raise RuntimeError(data.get("message","Twelve Data error"))
                bars=[]
                for r in reversed(data.get("values",[])):
                    try:bars.append({"time":r.get("datetime"),"open":float(r["open"]),"high":float(r["high"]),"low":float(r["low"]),"close":float(r["close"]),"volume":float(r.get("volume") or 0)})
                    except:pass
                if len(bars)>=30:
                    has_vol=sum(b["volume"] for b in bars[-30:])>0
                    return {"bars":bars,"source":f"Twelve Data {_symbol_td(sym)}","volume_type":"provider/tick volume" if has_vol else "no centralized volume; price-only technical analysis","freshness":1.0,"is_proxy":False,"instrument":_symbol_td(sym),"price_data_real":True}
            except Exception as e:errors.append(f"Twelve Data: {type(e).__name__}")
        # OANDA exact-instrument fallback for FX and spot metals when user has credentials.
        token=credentials.get("oanda_token") or os.environ.get("OANDA_TOKEN")
        if token and (_is_fx_pair(sym) or sym in {"XAUUSD","XAGUSD"}):
            try:
                inst=_symbol_oanda(sym);params=urllib.parse.urlencode({"granularity":_oanda_granularity(timeframe),"count":240,"price":"M"})
                data=_get_json(f"https://api-fxpractice.oanda.com/v3/instruments/{inst}/candles?{params}",{"Authorization":f"Bearer {token}","User-Agent":"NIGHT-Terminal/1.0"});bars=[]
                for c in data.get("candles",[]):
                    m=c.get("mid") or {}
                    if m:bars.append({"time":c.get("time"),"open":float(m["o"]),"high":float(m["h"]),"low":float(m["l"]),"close":float(m["c"]),"volume":float(c.get("volume",0))})
                if len(bars)>=30:return {"bars":bars,"source":f"OANDA {inst}","volume_type":"tick volume (price-update count)","freshness":1.0,"is_proxy":False,"instrument":inst,"price_data_real":True}
            except Exception as e:errors.append(f"OANDA: {type(e).__name__}")
        # Crypto public exchange fallback.
        bsym=_binance_symbol(sym)
        if bsym:
            try:
                interval={"1m":"1m","5m":"5m","15m":"15m","1h":"1h","4h":"4h","1D":"1d","1d":"1d"}.get(timeframe,"5m")
                rows=_get_json(f"https://api.binance.com/api/v3/klines?symbol={bsym}&interval={interval}&limit=240")
                bars=[{"time":r[0],"open":float(r[1]),"high":float(r[2]),"low":float(r[3]),"close":float(r[4]),"volume":float(r[5])} for r in rows]
                if len(bars)>=30:return {"bars":bars,"source":f"Binance {bsym} realtime/public","volume_type":"exchange-traded volume","freshness":1.0,"is_proxy":False,"instrument":bsym,"price_data_real":True}
            except Exception as e:errors.append(f"Binance: {type(e).__name__}")
        return {"bars":[],"source":"none","volume_type":"none","freshness":0.0,"provider_errors":errors,"is_proxy":False,"instrument":_symbol_td(sym),"price_data_real":False}

class MacroProvider:
    def _fred_series(self,series_id,key,limit=40):
        params=urllib.parse.urlencode({"series_id":series_id,"api_key":key,"file_type":"json","sort_order":"desc","limit":limit});data=_get_json(f"https://api.stlouisfed.org/fred/series/observations?{params}");vals=[]
        for r in reversed(data.get("observations",[])):
            try:vals.append(float(r["value"]))
            except:pass
        return vals
    async def snapshot(self,symbol,credentials=None):
        credentials=credentials or {};key=credentials.get("fred_key") or os.environ.get("FRED_API_KEY")
        if not key:return {"macro_score":0.0,"intermarket_score":0.0,"freshness":0.7,"macro_source":"neutral: FRED key not configured"}
        try:
            y10=self._fred_series("DGS10",key);real10=self._fred_series("DFII10",key);y2=self._fred_series("DGS2",key);unrate=self._fred_series("UNRATE",key,24);cpi=self._fred_series("CPIAUCSL",key,36)
            z10=_z_last_change(y10);zr=_z_last_change(real10);z2=_z_last_change(y2);zu=_z_last_change(unrate);yoy=[(cpi[i]/cpi[i-12]-1)*100 for i in range(12,len(cpi)) if cpi[i-12]!=0];zc=_z_last_change(yoy);gold_impulse=(-.34*_squash(zr)-.22*_squash(z10)-.16*_squash(z2)+.18*_squash(zu)+.10*_squash(zc));sym=symbol.upper()
            if sym=="XAUUSD":score=gold_impulse
            elif sym.endswith("USD") and sym!="USDJPY":score=-gold_impulse*.45
            elif sym.startswith("USD"):score=gold_impulse*.40
            else:score=0.0
            return {"macro_score":max(-1,min(1,score)),"intermarket_score":max(-1,min(1,-.45*_squash(zr)-.25*_squash(z10)-.15*_squash(z2))),"freshness":.9,"macro_source":"FRED official","macro_details":{"DGS10_change_z":round(z10,3),"DFII10_change_z":round(zr,3),"DGS2_change_z":round(z2,3),"UNRATE_change_z":round(zu,3),"CPI_yoy_change_z":round(zc,3)}}
        except Exception as e:return {"macro_score":0.0,"intermarket_score":0.0,"freshness":.5,"macro_source":f"FRED error: {type(e).__name__}"}
    async def calendar(self):return [{"time":None,"currency":"USD","event":"TradingView calendar widget available in frontend; structured surprise API connector pending","impact":"INFO","forecast":"—","previous":"—"}]
