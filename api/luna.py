from __future__ import annotations
import json, os, urllib.request, urllib.error

SYSTEM="""You are Luna AI, the institutional market-intelligence assistant inside NIGHT Terminal.
Answer naturally, directly, and in clean readable prose. Use supplied NIGHT context as supporting evidence, not as text to repeat.

CRITICAL RESPONSE RULES:
- NEVER print, echo, paste, serialize, or reproduce the raw NIGHT context, JSON, arrays, dictionaries, API payloads, COT rows, SEC objects, vessel arrays, or provider responses.
- NEVER output long sequences of raw numbers or repeated words from context.
- Summarize relevant data into a few human-readable conclusions only.
- If the user says hello or asks a casual/general question, answer that question normally and DO NOT dump market context.
- Only mention context fields that materially answer the user's question.
- If a dataset is large, aggregate it instead of listing records.
- Distinguish live, delayed/EOD, and latest-reported data.
- Never invent unavailable metrics.
- Never reveal internal quant formulas; explain conclusions and evidence instead.
- If current information is missing, say so clearly.

You can discuss equities, indices, FX, metals, commodities, macro, fundamentals, earnings, filings, geopolitics, shipping, risk, market structure, and news-event transmission. When analyzing news, separate what is already released from expectations, explain hawkish/dovish/neutral implications, affected assets, confidence, conflicting evidence, and invalidation."""

def _post(url,payload,headers,timeout=45):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method="POST")
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        raw=e.read().decode(errors="replace")
        try:
            d=json.loads(raw);msg=((d.get("error") or {}).get("message") if isinstance(d,dict) else None) or raw[:300]
        except Exception:msg=raw[:300]
        raise RuntimeError(f"OpenRouter HTTP {e.code}: {msg}")
    try:return json.loads(raw)
    except Exception:raise RuntimeError("OpenRouter returned a non-JSON response: "+raw[:180])

def _clip(v, n=280):
    s=str(v)
    return s if len(s)<=n else s[:n]+"…"

def _tf_summary(m):
    if not isinstance(m,dict):return None
    out={k:m.get(k) for k in ("action","probability_up","agreement","average_readiness","valid") if k in m}
    tfs=m.get("timeframes") if isinstance(m.get("timeframes"),dict) else {}
    if tfs:
        out["timeframes"]={tf:{k:r.get(k) for k in ("action","probability_up","trade_readiness") if k in r} for tf,r in list(tfs.items())[:6] if isinstance(r,dict)}
    return out

def _analysis_summary(a):
    if not isinstance(a,dict):return None
    keys=("action","bias","probability_up","trade_readiness","regime","ev_long_r","ev_short_r","macro_source","event_risk","source","data_quality","last_price")
    return {k:a.get(k) for k in keys if k in a}

def _equity_summary(e):
    if not isinstance(e,dict):return None
    q=e.get("quote") if isinstance(e.get("quote"),dict) else {}
    sig=e.get("signal") if isinstance(e.get("signal"),dict) else {}
    ship=e.get("shipping_exposure") if isinstance(e.get("shipping_exposure"),dict) else {}
    return {
        "symbol":e.get("symbol"),"price":e.get("price"),"price_source":e.get("price_source"),"freshness":e.get("freshness"),
        "signal":{k:sig.get(k) for k in ("action","bias","probability_up","confidence","readiness") if k in sig},
        "quote":{k:q.get(k) for k in ("marketCap","regularMarketVolume","regularMarketChangePercent","trailingPE","forwardPE","epsTrailingTwelveMonths") if k in q},
        "shipping_exposure":{k:ship.get(k) for k in ("sensitivity","mode","risk_state","risk_score") if k in ship}
    }

def _sanitize_context(c):
    if not isinstance(c,dict):return {}
    n=c.get("news") if isinstance(c.get("news"),dict) else {}
    articles=[]
    for a in (n.get("articles") or [])[:6]:
        if isinstance(a,dict):articles.append({"title":_clip(a.get("title") or "",180),"domain":a.get("domain"),"seen":a.get("seen"),"sentiment":a.get("sentiment")})
    a=c.get("activity") if isinstance(c.get("activity"),dict) else {}
    ship=a.get("shipping") if isinstance(a.get("shipping"),dict) else {}
    ranked=[]
    for r in (c.get("ranked") or [])[:5]:
        if isinstance(r,dict):ranked.append({k:r.get(k) for k in ("symbol","action","score","agreement","probability_up","average_readiness","qualified") if k in r})
    return {
        "symbol":c.get("symbol"),"market":c.get("market"),"tab":c.get("tab"),"timeframe":c.get("timeframe"),
        "analysis":_analysis_summary(c.get("analysis")),
        "mtf":_tf_summary(c.get("mtf")),
        "equity":_equity_summary(c.get("equity")),
        "equityMtf":_tf_summary(c.get("equityMtf")),
        "ranked":ranked,
        "news":{"source":n.get("source"),"score":n.get("score"),"count":n.get("count"),"articles":articles},
        "activity":{"oil":a.get("oil") if isinstance(a.get("oil"),dict) else {},"shipping":{"count":ship.get("count"),"analytics":ship.get("analytics") if isinstance(ship.get("analytics"),dict) else {}}}
    }

def _openrouter(message,ctx,key):
    model=os.getenv("OPENROUTER_MODEL","openrouter/free")
    payload={"model":model,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":f"NIGHT TERMINAL CONTEXT (structured evidence; summarize, never echo raw):\n{ctx}\n\nUSER QUESTION:\n{message}"}],"temperature":0.22,"max_tokens":1200}
    d=_post("https://openrouter.ai/api/v1/chat/completions",payload,{"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"https://night-terminal.vercel.app","X-Title":"NIGHT Terminal","User-Agent":"NIGHT-Terminal/1.0"})
    return (((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip(),model

def ask_luna(message:str,context:dict|None=None,credentials:dict|None=None):
    credentials=credentials or {};key=(credentials.get("openrouter_key") or os.getenv("OPENROUTER_API_KEY") or "").strip()
    clean=_sanitize_context(context or {})
    ctx=json.dumps(clean,ensure_ascii=False,default=str)[:9000]
    if not key:return {"ok":False,"answer":"Open Data Keys and paste your OpenRouter API key to activate Luna AI.","model":None,"provider":"OpenRouter"}
    try:
        text,model=_openrouter(message,ctx,key)
        if text:return {"ok":True,"answer":text,"model":model,"provider":"OpenRouter"}
        return {"ok":False,"answer":"OpenRouter returned an empty response. Try again; the free router may be temporarily out of capacity.","model":model,"provider":"OpenRouter"}
    except Exception as e:
        msg=str(e)
        if "401" in msg:return {"ok":False,"answer":"OpenRouter rejected the API key (401). Re-save the key in Data Keys.","model":None,"provider":"OpenRouter"}
        if "429" in msg:return {"ok":False,"answer":"OpenRouter free-tier rate limit/capacity reached. Try again shortly.","model":None,"provider":"OpenRouter"}
        return {"ok":False,"answer":"Luna/OpenRouter error: "+msg[:350],"model":None,"provider":"OpenRouter"}
