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

def _request_text(url,timeout=12):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 NIGHT-Terminal/1.0","Accept":"application/json,text/csv,*/*"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode("utf-8",errors="replace")

def _json(url,timeout=12):return json.loads(_request_text(url,timeout))

def _fred_api(series,key,limit=72):
 p=urllib.parse.urlencode({"series_id":series,"api_key":key,"file_type":"json","sort_order":"desc","limit":limit})
 d=_json("https://api.stlouisfed.org/fred/series/observations?"+p);out=[]
 for x in reversed(d.get("observations",[])):
  try:out.append((x.get("date"),float(x.get("value"))))
  except Exception:pass
 return out

def _fred_csv(series,limit=72):
 text=_request_text("https://fred.stlouisfed.org/graph/fredgraph.csv?id="+urllib.parse.quote(series),15)
 rows=[]
 for row in csv.DictReader(io.StringIO(text)):
  try:
   v=row.get(series)
   if v not in (None,"","."):rows.append((row.get("DATE") or row.get("observation_date"),float(v)))
  except Exception:pass
 return rows[-limit:]

def _fred(series,key=None,limit=72):
 errors=[]
 if key:
  try:
   rows=_fred_api(series,key,limit)
   if len(rows)>=2:return rows,"FRED API"
  except Exception as e:errors.append("api:"+type(e).__name__)
 try:
  rows=_fred_csv(series,limit)
  if len(rows)>=2:return rows,"FRED CSV"
 except Exception as e:errors.append("csv:"+type(e).__name__)
 raise RuntimeError(f"FRED series {series} unavailable ({', '.join(errors) or 'no rows'})")

def _changes(vals):
 if len(vals)<2:return[]
 return [vals[i][1]-vals[i-1][1] for i in range(1,len(vals))]

def _corr(a,b):
 n=min(len(a),len(b),48)
 if n<8:return 0.0
 a,b=a[-n:],b[-n:];ma=sum(a)/n;mb=sum(b)/n
 va=sum((x-ma)**2 for x in a);vb=sum((x-mb)**2 for x in b)
 if va<=0 or vb<=0:return 0.0
 return max(-1,min(1,sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(va*vb)))

def _z_last(ch):
 if len(ch)<5:return 0.0
 hist=ch[-25:-1] or ch[:-1];mu=sum(hist)/len(hist);sd=(sum((x-mu)**2 for x in hist)/max(1,len(hist)-1))**.5
 return 0.0 if sd==0 else max(-3,min(3,(ch[-1]-mu)/sd))

def _soft_probs(score,confidence):
 s=max(-3,min(3,score));strength=min(.82,.14+abs(s)*.20+(confidence/100)*.18)
 neutral=max(.08,.52-strength*.45);direction=(1-neutral)*(.5+.38*math.tanh(s))
 haw=direction if s>=0 else (1-neutral)-direction;dov=(1-neutral)-haw
 if abs(s)<.16:haw=dov=(1-neutral)/2
 total=haw+dov+neutral
 return round(haw/total*100,1),round(dov/total*100,1),round(neutral/total*100,1)

def event_catalog():return [{"id":k,"label":v["label"]} for k,v in EVENTS.items()]

def predict_event(event:str,credentials:dict|None=None):
 credentials=credentials or {};key=(credentials.get("fred_key") or os.getenv("FRED_API_KEY") or "").strip();e=ALIASES.get(event.strip().upper(),event.strip().upper());cfg=EVENTS.get(e)
 if not cfg:return {"ok":False,"event":e,"error":"Unsupported event","available_events":event_catalog()}
 try:target,target_source=_fred(cfg["target"],key)
 except Exception as ex:return {"ok":False,"event":e,"label":cfg["label"],"error":"Target data unavailable: "+str(ex)[:180],"available_events":event_catalog()}
 tch=_changes(target);evidence=[];score=0.0;weight_sum=0.0;sources={target_source}
 for sid,name,effect,w in cfg["drivers"]:
  try:rows,src=_fred(sid,key);sources.add(src);ch=_changes(rows)
  except Exception:continue
  if len(rows)<2 or not ch:continue
  corr=_corr(tch,ch);z=_z_last(ch);reliability=.35+.65*abs(corr);contrib=effect*w*z*reliability;score+=contrib;weight_sum+=w
  latest,prev=rows[-1],rows[-2];signal="HAWKISH" if contrib>.12 else "DOVISH" if contrib<-.12 else "NEUTRAL"
  evidence.append({"series_id":sid,"name":name,"source":src,"latest_date":latest[0],"latest":round(latest[1],4),"previous_date":prev[0],"previous":round(prev[1],4),"change":round(latest[1]-prev[1],4),"normalized_move":round(z,3),"historical_correlation":round(corr,3),"weight":w,"policy_effect":"hawkish when rising" if effect>0 else "dovish when rising","signal":signal,"contribution":round(contrib,3)})
 if weight_sum:score/=weight_sum
 if len(tch):score+=.18*cfg.get("target_hawk",1)*_z_last(tch)
 avgcorr=sum(abs(x["historical_correlation"]) for x in evidence)/len(evidence) if evidence else 0
 confidence=min(92,28+len(evidence)*7+avgcorr*30+min(18,abs(score)*12))
 haw,dov,neu=_soft_probs(score,confidence);stance="HAWKISH" if haw>max(dov,neu) else "DOVISH" if dov>max(haw,neu) else "NEUTRAL"
 target_latest=target[-1] if target else (None,None);target_prev=target[-2] if len(target)>1 else (None,None)
 evidence.sort(key=lambda x:abs(x["contribution"]),reverse=True)
 proof=[f'{x["name"]}: {x["signal"]} (latest change {x["change"]:+g}, historical corr {x["historical_correlation"]:+.2f})' for x in evidence[:5]]
 explanation=(f'{cfg["label"]} pre-release model leans {stance.lower()} because the strongest currently released lead indicators are '+('; '.join(proof[:3]) if proof else 'not available')+'. Percentages are evidence-weighted scenarios, not a guarantee of the release result.')
 return {"ok":True,"event":e,"label":cfg["label"],"data_source":" + ".join(sorted(sources)),"target":{"series_id":cfg["target"],"name":cfg["target_name"],"source":target_source,"latest_date":target_latest[0],"latest":target_latest[1],"previous_date":target_prev[0],"previous":target_prev[1]},"stance":stance,"hawkish_pct":hawk,"dovish_pct":dov,"neutral_pct":neu,"evidence_confidence_pct":round(confidence,1),"model_score":round(score,4),"evidence":evidence,"news_proof":proof,"explanation":explanation,"method":"pre-release lead-indicator model using latest released macro series plus their historical directional relationship to the selected event","updated_at":datetime.now(timezone.utc).isoformat(),"available_events":event_catalog()}
