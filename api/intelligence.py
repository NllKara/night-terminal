from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


def _get_text(url: str, timeout: int = 12):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NIGHT-Terminal/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _get_json(url: str, timeout: int = 12):
    return json.loads(_get_text(url, timeout))


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _news_query(symbol: str) -> str:
    s=symbol.upper()
    mapping={
        "XAUUSD":"gold Federal Reserve Treasury yields dollar inflation",
        "XAGUSD":"silver Federal Reserve dollar yields metals",
        "BTCUSD":"bitcoin crypto Federal Reserve dollar ETF",
        "ETHUSD":"ethereum crypto Federal Reserve ETF",
        "NAS100":"Nasdaq technology stocks Federal Reserve yields",
        "SPX500":"S&P 500 stocks Federal Reserve economy",
        "US30":"Dow Jones stocks Federal Reserve economy",
    }
    if s in mapping:return mapping[s]
    if len(s)==6 and s.isalpha():return f"{s[:3]} {s[3:]} forex central bank rates economy"
    return f"{s} markets economy Federal Reserve"


def _event_query(event: str) -> str:
    e=event.strip().upper()
    mapping={
        "NFP":"US nonfarm payrolls jobs report unemployment wages Federal Reserve",
        "CPI":"US CPI inflation consumer prices Federal Reserve",
        "CORE CPI":"US core CPI inflation Federal Reserve",
        "FOMC":"Federal Reserve FOMC rate decision Powell",
        "POWELL":"Jerome Powell Federal Reserve speech rates inflation",
        "PCE":"US PCE inflation Federal Reserve core PCE",
        "GDP":"US GDP economic growth Federal Reserve",
        "CLAIMS":"US jobless claims unemployment claims labor market",
        "RETAIL SALES":"US retail sales consumer spending economy",
        "PPI":"US producer price inflation PPI Federal Reserve",
        "GEOPOLITICS":"war sanctions tariffs Middle East China Russia shipping oil markets",
    }
    return mapping.get(e, event)


def _headline_score(title: str, symbol: str) -> float:
    t=title.lower(); s=symbol.upper()
    pos=["rises","gains","surges","beats","strong demand","rate cut","dovish","yields fall","dollar falls","cooler inflation","slower inflation"]
    neg=["falls","drops","slumps","misses","weak demand","rate hike","hawkish","yields rise","dollar rises","hotter inflation","inflation accelerates"]
    raw=sum(1 for k in pos if k in t)-sum(1 for k in neg if k in t)
    if s=="XAUUSD":
        raw+=sum(1 for k in ["safe haven","geopolitical tensions","gold rises","gold gains"] if k in t)
        raw-=sum(1 for k in ["gold falls","gold drops","ceasefire"] if k in t)
    return math.tanh(raw/2.0)


def _policy_score(title: str) -> float:
    t=title.lower()
    hawkish=["hawkish","rate hike","higher for longer","inflation sticky","inflation hot","strong jobs","wage growth","tight labor","no rush to cut","fewer cuts","above forecast","beats forecast"]
    dovish=["dovish","rate cut","cooling inflation","inflation cools","weak jobs","job losses","unemployment rises","slower growth","more cuts","below forecast","misses forecast"]
    return _clamp((sum(1 for k in hawkish if k in t)-sum(1 for k in dovish if k in t))/3.0)


def _gdelt(query: str, max_records: int) -> list[dict]:
    params=urllib.parse.urlencode({"query":query,"mode":"ArtList","maxrecords":max_records,"format":"json","sort":"HybridRel"})
    data=_get_json(f"https://api.gdeltproject.org/api/v2/doc/doc?{params}")
    out=[]
    for a in data.get("articles",[])[:max_records]:
        title=(a.get("title") or "").strip()
        if title:out.append({"title":title,"url":a.get("url"),"domain":a.get("domain"),"seen":a.get("seendate"),"language":a.get("language"),"country":a.get("sourcecountry")})
    return out


def _google_news(query: str, max_records: int) -> list[dict]:
    q=urllib.parse.quote_plus(query+" when:1d")
    xml=_get_text(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")
    root=ET.fromstring(xml);out=[]
    for item in root.findall(".//item")[:max_records]:
        title=(item.findtext("title") or "").strip(); link=(item.findtext("link") or "").strip(); pub=(item.findtext("pubDate") or "").strip();src=item.find("source")
        if title:out.append({"title":title,"url":link,"domain":src.text if src is not None else "Google News","seen":pub,"language":"English","country":None})
    return out


def _fetch_rows(query: str, max_records: int) -> tuple[list[dict],str,list[str]]:
    errors=[]
    try:
        rows=_gdelt(query,max_records)
        if rows:return rows,"GDELT DOC 2.0",errors
    except Exception as e:errors.append("GDELT "+type(e).__name__)
    try:
        rows=_google_news(query,max_records)
        if rows:return rows,"Google News RSS fallback",errors
    except Exception as e:errors.append("GoogleNews "+type(e).__name__)
    return [],"No live source",errors


def fetch_news(symbol: str, max_records: int = 24) -> dict:
    rows,source,errors=_fetch_rows(_news_query(symbol),max_records);scores=[];clean=[]
    for a in rows:
        sc=_headline_score(a["title"],symbol);scores.append(sc);clean.append({**a,"sentiment":round(sc,3),"policy_score":round(_policy_score(a["title"]),3)})
    score=sum(scores)/len(scores) if scores else 0.0
    return {"source":source,"score":round(_clamp(score),4),"count":len(clean),"articles":clean,"updated_at":datetime.now(timezone.utc).isoformat(),"errors":errors}


def fetch_event_news(event: str, max_records: int = 30) -> dict:
    rows,source,errors=_fetch_rows(_event_query(event),max_records);policy=[];clean=[]
    for a in rows:
        ps=_policy_score(a["title"]);policy.append(ps);clean.append({**a,"policy_score":round(ps,3)})
    avg=sum(policy)/len(policy) if policy else 0.0
    haw=max(0.0,avg);dov=max(0.0,-avg);neu=max(0.15,1.0-abs(avg));total=haw+dov+neu
    haw,dov,neu=[x/total*100 for x in (haw,dov,neu)]
    evidence=min(95.0,25.0+len(clean)*2.0+abs(avg)*35.0)
    return {"event":event,"source":source,"count":len(clean),"articles":clean,"hawkish_pct":round(haw,1),"dovish_pct":round(dov,1),"neutral_pct":round(neu,1),"evidence_confidence_pct":round(evidence,1),"policy_score":round(avg,4),"updated_at":datetime.now(timezone.utc).isoformat(),"errors":errors}


def fetch_cot_gold(limit: int = 52) -> dict:
    try:
        where="upper(market_and_exchange_names) like '%GOLD%'";params=urllib.parse.urlencode({"$limit":limit,"$where":where,"$order":"report_date_as_yyyy_mm_dd DESC"});rows=_get_json(f"https://publicreporting.cftc.gov/resource/72hh-3qpy.json?{params}");parsed=[]
        for r in rows:
            try:
                long_v=float(r.get("m_money_positions_long_all",0) or 0);short_v=float(r.get("m_money_positions_short_all",0) or 0);oi=float(r.get("open_interest_all",0) or 0);net=long_v-short_v;norm=net/oi if oi else 0.0;parsed.append({"date":r.get("report_date_as_yyyy_mm_dd"),"market":r.get("market_and_exchange_names"),"managed_money_long":long_v,"managed_money_short":short_v,"managed_money_net":net,"open_interest":oi,"net_pct_oi":norm})
            except Exception:continue
        if not parsed:return {"source":"CFTC PRE","score":0.0,"rows":[]}
        hist=[x["net_pct_oi"] for x in parsed];latest=hist[0];mu=sum(hist)/len(hist);sd=(sum((x-mu)**2 for x in hist)/max(1,len(hist)-1))**0.5;z=0.0 if sd==0 else (latest-mu)/sd;score=math.tanh(z/2.0)
        return {"source":"CFTC Disaggregated Futures Only","score":round(_clamp(score),4),"zscore":round(z,3),"latest":parsed[0],"rows":parsed}
    except Exception as e:return {"source":"CFTC PRE","score":0.0,"rows":[],"error":type(e).__name__}


def intelligence_snapshot(symbol: str) -> dict:
    news=fetch_news(symbol);cot=fetch_cot_gold() if symbol.upper()=="XAUUSD" else {"source":"CFTC PRE","score":0.0,"rows":[]};return {"news":news,"cot":cot}
