from __future__ import annotations

import csv, io, json, math, os, urllib.parse, urllib.request
from datetime import datetime, timezone

EVENTS={
 "NFP":{"label":"Nonfarm Payrolls","target":"PAYEMS","target_name":"Nonfarm Payrolls","target_hawk":1,"drivers":[("ADPMNUSNERSA","ADP Private Payrolls",1,1.25),("UNRATE","Unemployment Rate",-1,1.15),("ICSA","Initial Jobless Claims",-1,1.0),("JTSJOL","JOLTS Job Openings",1,.85),("CES0500000003","Average Hourly Earnings",1,.7)]},
 "UNEMPLOYMENT":{"label":"Unemployment Rate","target":"UNRATE","target_name":"Unemployment Rate","target_hawk":-1,"drivers":[("ICSA","Initial Jobless Claims",-1,1.2),("ADPMNUSNERSA","ADP Private Payrolls",1,1.0),("JTSJOL","JOLTS Job Openings",1,.85),("PAYEMS","Nonfarm Payrolls",1,.9)]},
 "ADP":{"label":"ADP Employment","target":"ADPMNUSNERSA","target_name":"ADP Private Payrolls","target_hawk":1,"drivers":[("ICSA","Initial Jobless Claims",-1,1.1),("UNRATE","Unemployment Rate",-1,.9),("JTSJOL","JOLTS Job Openings",1,.9),("PAYEMS","Nonfarm Payrolls",1,.8)]},
 "CLAIMS":{"label":"Initial Jobless Claims","target":"ICSA","target_name":"Initial Jobless Claims","target_hawk":-1,"drivers":[("UNRATE","Unemployment Rate",-1,.9),("ADPMNUSNERSA","ADP Private Payrolls",1,.8),("PAYEMS","Nonfarm Payrolls",1,.8)]},
 "JOLTS":{"label":"JOLTS Job Openings","target":"JTSJOL","target_name":"JOLTS Job Openings","target_hawk":1,"drivers":[("ICSA","Initial Jobless Claims",-1,.9),("UNRATE","Unemployment Rate",-1,.8),("ADPMNUSNERSA","ADP Private Payrolls",1,.8)]},
 "CPI":{"label":"CPI Inflation","target":"CPIAUCSL","target_name":"Headline CPI","target_hawk":1,"drivers":[("CPILFESL","Core CPI",1,1.15),("PPIACO","Producer Prices",1,1.0),("PCEPI","PCE Price Index",1,.9),("PCEPILFE","Core PCE",1,1.0),("DCOILWTICO","WTI Crude Oil",1,.7),("CES0500000003","Average Hourly Earnings",1,.65)]},
 "CORE CPI":{"label":"Core CPI","target":"CPILFESL","target_name":"Core CPI","target_hawk":1,"drivers":[("CPIAUCSL","Headline CPI",1,1.0),("PCEPILFE","Core PCE",1,1.1),("PPIACO","Producer Prices",1,.9),("CES0500000003","Average Hourly Earnings",1,.7)]},
 "PPI":{"label":"Producer Price Inflation","target":"PPIACO","target_name":"PPI","target_hawk":1,"drivers":[("DCOILWTICO","WTI Crude Oil",1,1.0),("CPIAUCSL","Headline CPI",1,.8),("PCEPI","PCE Price Index",1,.7)]},
 "PCE":{"label":"PCE Inflation","target":"PCEPI","target_name":"PCE Price Index","target_hawk":1,"drivers":[("CPIAUCSL","Headline CPI",1,1.0),("CPILFESL","Core CPI",1,.95),("PPIACO","Producer Prices",1,.8),("CES0500000003","Average Hourly Earnings",1,.7)]},
 "CORE PCE":{"label":"Core PCE Inflation","target":"PCEPILFE","target_name":"Core PCE","target_hawk":1,"drivers":[("CPILFESL","Core CPI",1,1.15),("CPIAUCSL","Headline CPI",1,.8),("CES0500000003","Average Hourly Earnings",1,.8),("PPIACO","Producer Prices",1,.65)]},
 "RETAIL SALES":{"label":"Retail Sales","target":"RSAFS","target_name":"Retail Sales","target_hawk":1,"drivers":[("PCE","Personal Consumption Expenditures",1,1.0),("UMCSENT","Michigan Consumer Sentiment",1,.8),("UNRATE","Unemployment Rate",-1,.65),("PAYEMS","Nonfarm Payrolls",1,.7)]},
 "GDP":{"label":"GDP Growth","target":"GDPC1","target_name":"Real GDP","target_hawk":1,"drivers":[("INDPRO","Industrial Production",1,.9),("RSAFS","Retail Sales",1,.85),("PAYEMS","Nonfarm Payrolls",1,.75),("UNRATE","Unemployment Rate",-1,.65)]},
 "DURABLE GOODS":{"label":"Durable Goods Orders","target":"DGORDER","target_name":"Durable Goods Orders","target_hawk":1,"drivers":[("INDPRO","Industrial Production",1,.9),("MANEMP","Manufacturing Employment",1,.7),("PAYEMS","Nonfarm Payrolls",1,.6)]},
 "HOUSING STARTS":{"label":"Housing Starts","target":"HOUST","target_name":"Housing Starts","target_hawk":1,"drivers":[("PERMIT","Building Permits",1,1.15),("MORTGAGE30US","30Y Mortgage Rate",-1,.7),("UNRATE","Unemployment Rate",-1,.5)]},
 "CONSUMER SENTIMENT":{"label":"Michigan Consumer Sentiment","target":"UMCSENT","target_name":"Consumer Sentiment","target_hawk":1,"drivers":[("UNRATE","Unemployment Rate",-1,.7),("CPIAUCSL","Headline CPI",-1,.65),("RSAFS","Retail Sales",1,.75)]},
 "INDUSTRIAL PRODUCTION":{"label":"Industrial Production","target":"INDPRO","target_name":"Industrial Production","target_hawk":1,"drivers":[("PAYEMS","Nonfarm Payrolls",1,.65),("MANEMP","Manufacturing Employment",1,.9),("RSAFS","Retail Sales",1,.55)]},
 "FOMC":{"label":"FOMC Rate Decision","target":"FEDFUNDS","target_name":"Effective Fed Funds Rate","target_hawk":1,"drivers":[("PCEPILFE","Core PCE",1,1.25),("CPILFESL","Core CPI",1,1.1),("UNRATE","Unemployment Rate",-1,1.0),("PAYEMS","Nonfarm Payrolls",1,.9),("CES0500000003","Average Hourly Earnings",1,.75)]},
}
ALIASES={"NONFARM PAYROLLS":"NFP","UNEMPLOYMENT RATE":"UNEMPLOYMENT","JOBLESS CLAIMS":"CLAIMS","INITIAL CLAIMS":"CLAIMS","CORE PPI":"PPI","HEADLINE CPI":"CPI","MICHIGAN SENTIMENT":"CONSUMER SENTIMENT","FED":"FOMC"}
BLS_MAP={"PAYEMS":"CES0000000001","UNRATE":"LNS14000000","CES0500000003":"CES0500000003","CPIAUCSL":"CUSR0000SA0","CPILFESL":"CUSR0000SA0L1E"}

def _json(url,timeout=8):
 req=urllib.request.Request(url,headers={"User-Agent":"NIGHT-Terminal/1.0","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())

def _fred_api(series,key,limit=72):
 if not key:raise RuntimeError("no FRED key")
 p=urllib.parse.urlencode({"series_id":series,"api_key":key,"file_type":"json","sort_order":"desc","limit":limit})
 d=_json("https://api.stlouisfed.org/fred/series/observations?"+p,6);out=[]
 for x in reversed(d.get("observations",[])):
  try:out.append((x.get("date"),float(x.get("value"))))
  except:pass
 if len(out)<2:raise RuntimeError("empty FRED API series")
 return out,"FRED API"

def _fred_csv(series,limit=72):
 url="https://fred.stlouisfed.org/graph/fredgraph.csv?id="+urllib.parse.quote(series)
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 NIGHT-Terminal"})
 with urllib.request.urlopen(req,timeout=6) as r:text=r.read().decode("utf-8","replace")
 rows=list(csv.DictReader(io.StringIO(text)));out=[]
 for x in rows:
  try:out.append((x.get("DATE") or x.get("observation_date"),float(x.get(series))))
  except:pass
 if len(out)<2:raise RuntimeError("empty FRED CSV series")
 return out[-limit:],"FRED CSV"

def _bls(series,limit=72):
 bid=BLS_MAP.get(series)
 if not bid:raise RuntimeError("no BLS mapping")
 d=_json("https://api.bls.gov/publicAPI/v2/timeseries/data/"+urllib.parse.quote(bid),7)
 series_rows=((d.get("Results") or {}).get("series") or [])
 if not series_rows:raise RuntimeError("empty BLS series")
 out=[]
 for x in reversed(series_rows[0].get("data") or []):
  period=x.get("period","")
  if not period.startswith("M") or period=="M13":continue
  try:out.append((f'{x.get("year")}-{int(period[1:]):02d}-01',float(x.get("value"))))
  except:pass
 if len(out)<2:raise RuntimeError("insufficient BLS data")
 return out[-limit:],"BLS Public API"

def _series(series,key,limit=72):
 errors=[]
 for fn in ((_fred_api if key else None),_bls,_fred_csv):
  if not fn:continue
  try:
   return fn(series,key,limit) if fn==_fred_api else fn(series,limit)
  except Exception as ex:errors.append(type(ex).__name__)
 raise RuntimeError(f'{series} unavailable ({"/".join(errors)})')

def _changes(vals):return [vals[i][1]-vals[i-1][1] for i in range(1,len(vals))] if len(vals)>1 else []
def _corr(a,b):
 n=min(len(a),len(b),36)
 if n<6:return 0.0
 a,b=a[-n:],b[-n:];ma=sum(a)/n;mb=sum(b)/n;va=sum((x-ma)**2 for x in a);vb=sum((x-mb)**2 for x in b)
 return 0.0 if va<=0 or vb<=0 else max(-1,min(1,sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(va*vb)))
def _z_last(ch):
 if len(ch)<5:return 0.0
 hist=ch[-25:-1] or ch[:-1];mu=sum(hist)/len(hist);sd=(sum((x-mu)**2 for x in hist)/max(1,len(hist)-1))**.5
 return 0.0 if sd==0 else max(-3,min(3,(ch[-1]-mu)/sd))
def _soft_probs(score,confidence):
 s=max(-3,min(3,score));strength=min(.82,.14+abs(s)*.20+(confidence/100)*.18);neutral=max(.08,.52-strength*.45);direction=(1-neutral)*(.5+.38*math.tanh(s));haw=direction if s>=0 else (1-neutral)-direction;dov=(1-neutral)-haw
 if abs(s)<.16:haw=dov=(1-neutral)/2
 total=haw+dov+neutral;return round(haw/total*100,1),round(dov/total*100,1),round(neutral/total*100,1)
def event_catalog():return [{"id":k,"label":v["label"]} for k,v in EVENTS.items()]

def predict_event(event:str,credentials:dict|None=None):
 credentials=credentials or {};key=(credentials.get("fred_key") or os.getenv("FRED_API_KEY") or "").strip();e=ALIASES.get(event.strip().upper(),event.strip().upper());cfg=EVENTS.get(e)
 if not cfg:return {"ok":False,"event":e,"error":"Unsupported event","available_events":event_catalog()}
 try:target,target_source=_series(cfg["target"],key)
 except Exception as ex:return {"ok":False,"event":e,"label":cfg["label"],"error":"Target data unavailable: "+str(ex),"available_events":event_catalog()}
 tch=_changes(target);evidence=[];score=0.0;weight_sum=0.0;skipped=[]
 for sid,name,effect,w in cfg["drivers"]:
  try:rows,source=_series(sid,key);ch=_changes(rows)
  except Exception as ex:skipped.append({"series_id":sid,"name":name,"reason":str(ex)});continue
  if len(rows)<2 or not ch:continue
  corr=_corr(tch,ch);z=_z_last(ch);reliability=.35+.65*abs(corr);contrib=effect*w*z*reliability;score+=contrib;weight_sum+=w;latest,prev=rows[-1],rows[-2];signal="HAWKISH" if contrib>.12 else "DOVISH" if contrib<-.12 else "NEUTRAL"
  evidence.append({"series_id":sid,"name":name,"source":source,"latest_date":latest[0],"latest":round(latest[1],4),"previous_date":prev[0],"previous":round(prev[1],4),"change":round(latest[1]-prev[1],4),"normalized_move":round(z,3),"historical_correlation":round(corr,3),"weight":w,"policy_effect":"hawkish when rising" if effect>0 else "dovish when rising","signal":signal,"contribution":round(contrib,3)})
 if weight_sum:score/=weight_sum
 if tch:score+=.18*cfg.get("target_hawk",1)*_z_last(tch)
 avgcorr=sum(abs(x["historical_correlation"]) for x in evidence)/len(evidence) if evidence else 0;confidence=min(92,28+len(evidence)*7+avgcorr*30+min(18,abs(score)*12));haw,dov,neu=_soft_probs(score,confidence);stance="HAWKISH" if haw>max(dov,neu) else "DOVISH" if dov>max(haw,neu) else "NEUTRAL";target_latest=target[-1];target_prev=target[-2];evidence.sort(key=lambda x:abs(x["contribution"]),reverse=True);proof=[f'{x["name"]}: {x["signal"]} (latest change {x["change"]:+g}, historical corr {x["historical_correlation"]:+.2f}, {x["source"]})' for x in evidence[:5]];explanation=f'{cfg["label"]} pre-release model leans {stance.lower()} because '+('; '.join(proof[:3]) if proof else 'usable leading evidence is limited')+'. Percentages are evidence-weighted scenarios, not a guarantee.'
 return {"ok":True,"event":e,"label":cfg["label"],"target":{"series_id":cfg["target"],"name":cfg["target_name"],"source":target_source,"latest_date":target_latest[0],"latest":target_latest[1],"previous_date":target_prev[0],"previous":target_prev[1]},"stance":stance,"hawkish_pct":haw,"dovish_pct":dov,"neutral_pct":neu,"evidence_confidence_pct":round(confidence,1),"model_score":round(score,4),"evidence":evidence,"skipped_evidence":skipped,"news_proof":proof,"explanation":explanation,"method":"pre-release lead-indicator model with official BLS fallback for payroll/labor/CPI series plus FRED for broader macro evidence","updated_at":datetime.now(timezone.utc).isoformat(),"available_events":event_catalog()}
