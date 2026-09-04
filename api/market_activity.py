from __future__ import annotations

import json, math, urllib.parse, urllib.request

CHOKEPOINTS={
 "Hormuz":(26.56,56.25,2.2),"Bab el-Mandeb":(12.58,43.34,2.0),"Suez":(30.45,32.35,2.1),"Malacca":(2.6,101.4,3.0),"Panama":(9.1,-79.7,1.8),"Singapore":(1.26,103.85,1.6),"Taiwan Strait":(24.3,119.6,3.0),"Cape of Good Hope":(-34.5,18.5,3.5)
}

def _get_json(url:str,headers:dict|None=None,timeout:int=12):
    h={"User-Agent":"NIGHT-Terminal/1.0","Accept-Encoding":"gzip"};h.update(headers or {})
    req=urllib.request.Request(url,headers=h)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=r.read()
        if (r.headers.get("Content-Encoding") or "").lower()=="gzip":
            import gzip;raw=gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))

def oil_snapshot()->dict:
    out={}
    for name,ticker in {"WTI":"CL=F","BRENT":"BZ=F","NATGAS":"NG=F"}.items():
        try:
            q=_get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?interval=5m&range=1d");r=(q.get("chart",{}).get("result") or [None])[0];meta=(r or {}).get("meta",{})
            out[name]={"price":meta.get("regularMarketPrice"),"previous_close":meta.get("chartPreviousClose"),"currency":meta.get("currency","USD"),"exchange":meta.get("exchangeName"),"source":"Yahoo futures (unofficial/free)"}
        except Exception:out[name]={"price":None,"source":"unavailable"}
    return out

def _type_blob(p):
    keys=("shipType","ship_type","shipTypeCode","ship_type_code","type","typeName","type_name","category","cargo","vesselType","vessel_type","aisType","ais_type","class")
    return " ".join(str(p.get(k) or "") for k in keys).lower()

def _type_code(p):
    # Open Waters /v1/vessels uses properties.type for the AIS ship/cargo code.
    for k in ("type","ship_type","shipType","shipTypeCode","ship_type_code","aisType","ais_type","typeCode"):
        try:
            v=int(float(p.get(k)))
            if 0<=v<=99:return v
        except Exception:pass
    return None

def _kind(p):
    raw=_type_blob(p);c=_type_code(p)
    if any(x in raw for x in ("lng tanker","lng carrier","liquefied natural gas")):return "LNG_TANKER"
    if any(x in raw for x in ("lpg tanker","lpg carrier","liquefied petroleum")):return "LPG_TANKER"
    if any(x in raw for x in ("chemical tanker","chem tanker")):return "CHEMICAL_TANKER"
    if any(x in raw for x in ("product tanker","oil products tanker")):return "PRODUCT_TANKER"
    if any(x in raw for x in ("crude tanker","crude oil tanker","vlcc","suezmax","aframax")):return "CRUDE_TANKER"
    if "tanker" in raw:return "TANKER"
    if any(x in raw for x in ("container ship","containership","container vessel")):return "CONTAINER"
    if any(x in raw for x in ("bulk carrier","bulker")):return "BULK_CARRIER"
    if any(x in raw for x in ("general cargo","cargo ship","freight")):return "GENERAL_CARGO"
    if any(x in raw for x in ("passenger","ferry","cruise")):return "PASSENGER"
    if any(x in raw for x in ("fishing","fish")):return "FISHING"
    if any(x in raw for x in ("tug","towing")):return "TUG"
    if any(x in raw for x in ("dredger","dredging")):return "DREDGER"
    if any(x in raw for x in ("pleasure","yacht")):return "PLEASURE"
    if any(x in raw for x in ("high speed","hsc")):return "HIGH_SPEED"
    # ITU/AIS ship and cargo type code ranges. Open Waters exposes this as properties.type.
    if c is not None:
        if 80<=c<=89:return "TANKER"
        if 70<=c<=79:return "CARGO"
        if 60<=c<=69:return "PASSENGER"
        if 40<=c<=49:return "HIGH_SPEED"
        if c==30:return "FISHING"
        if c in {31,32,52}:return "TUG"
        if c==33:return "DREDGER"
        if c in {36,37}:return "PLEASURE"
        if c in {50,51,53,54,55,56,57,58,59}:return "SERVICE"
    if any(x in raw for x in ("cargo","container","bulk")):return "CARGO"
    return "OTHER"

def _group(kind):
    if "TANKER" in kind:return "TANKER"
    if kind in {"CONTAINER","BULK_CARRIER","GENERAL_CARGO","CARGO"}:return "CARGO"
    return kind

def _near(lat,lon,clat,clon,deg):
    if lat is None or lon is None:return False
    return abs(float(lat)-clat)<=deg and abs(float(lon)-clon)<=deg

def shipping_snapshot(limit:int=700)->dict:
    """Global anonymous AIS snapshot from Open Waters. Coverage and static metadata depend on contributing feeds."""
    try:
        data=_get_json("https://ais.openwaters.io/v1/vessels",timeout=20);features=data.get("features",[]) if isinstance(data,dict) else [];vessels=[];types={};groups={"CARGO":0,"TANKER":0,"PASSENGER":0,"FISHING":0,"TUG":0,"SERVICE":0,"OTHER":0};chokes={k:0 for k in CHOKEPOINTS};moving=0;slow=0
        for f in features:
            p=f.get("properties",{}) or {};g=f.get("geometry",{}) or {};coords=g.get("coordinates") or [None,None];lon=coords[0] if coords else None;lat=coords[1] if len(coords)>1 else None;k=_kind(p);grp=_group(k);types[k]=types.get(k,0)+1;groups[grp]=groups.get(grp,0)+1
            speed=p.get("sog") if p.get("sog") is not None else p.get("speed")
            try:
                sp=float(speed or 0);moving+=1 if sp>2 else 0;slow+=1 if 0<sp<=2 else 0
            except Exception:pass
            for name,(a,b,d) in CHOKEPOINTS.items():
                if _near(lat,lon,a,b,d):chokes[name]+=1
            if len(vessels)<limit:
                vessels.append({"mmsi":p.get("mmsi"),"imo":p.get("imo"),"name":p.get("name") or p.get("shipName"),"lat":lat,"lon":lon,"speed":speed,"course":p.get("cog") or p.get("course"),"heading":p.get("heading"),"status":p.get("nav_status") if p.get("nav_status") is not None else p.get("navigationStatus") or p.get("status"),"destination":p.get("destination"),"callsign":p.get("callsign"),"type":k,"group":grp,"ais_type_code":_type_code(p),"raw_type":p.get("typeName") or p.get("shipType") or p.get("type"),"seen":p.get("seen"),"source":p.get("source"),"station":p.get("station"),"msg_type":p.get("msg_type")})
        total=len(features);congestion=max(chokes.values()) if chokes else 0
        return {"source":"Open Waters global AIS","coverage":"receiver/source dependent","count":total,"returned":len(vessels),"vessels":vessels,"analytics":{"types":types,"groups":groups,"chokepoints":chokes,"moving":moving,"slow":slow,"congestion_peak":congestion,"congestion_state":"HIGH" if congestion>=120 else "ELEVATED" if congestion>=60 else "NORMAL"}}
    except Exception as e:return {"source":"Open Waters global AIS","coverage":"unavailable","count":0,"returned":0,"vessels":[],"analytics":{"types":{},"groups":{},"chokepoints":{}},"error":type(e).__name__}

def shipping_exposure(symbol:str,profile:dict|None=None,shipping:dict|None=None)->dict:
    profile=profile or {};shipping=shipping or shipping_snapshot(350);text=" ".join(str(profile.get(k) or "") for k in ("sector","industry","description","name")).lower();sym=symbol.upper()
    if any(x in text for x in ("oil","gas","energy","petroleum","refining")):mode="TANKER";sensitivity="HIGH"
    elif any(x in text for x in ("mining","metal","steel","coal","materials","chemical")):mode="CARGO";sensitivity="HIGH"
    elif any(x in text for x in ("technology","semiconductor","electronics","consumer","retail","automotive","industrial")):mode="CARGO";sensitivity="MEDIUM"
    elif any(x in text for x in ("bank","finance","software","telecom","health")):mode="INDIRECT";sensitivity="LOW"
    else:mode="CARGO/INDIRECT";sensitivity="MEDIUM"
    relevant=[v for v in shipping.get("vessels",[]) if mode in {"CARGO","TANKER"} and v.get("group")==mode][:25]
    ch=(shipping.get("analytics") or {}).get("chokepoints",{});peak=max(ch.values()) if ch else 0;risk=25+(20 if sensitivity=="HIGH" else 10 if sensitivity=="MEDIUM" else 4)+(20 if peak>=120 else 10 if peak>=60 else 0);risk=min(100,risk)
    return {"symbol":sym,"mode":mode,"sensitivity":sensitivity,"risk_score":risk,"risk_state":"HIGH" if risk>=65 else "ELEVATED" if risk>=45 else "LOW","relevant_live_vessels":relevant,"chokepoints":ch,"disclaimer":"Relevant AIS vessels are shipping-network proxies, not verified carriers used by this company unless a public operator/fleet match is explicitly available."}

def activity_snapshot()->dict:return {"oil":oil_snapshot(),"shipping":shipping_snapshot()}
