from __future__ import annotations
import json, os, urllib.request, urllib.error

SYSTEM="""You are Luna AI, the institutional market-intelligence assistant inside NIGHT Terminal. Answer naturally and directly. Use supplied NIGHT context as the primary source for prices, quant state, fundamentals, live news, macro, geopolitics and shipping analytics. Distinguish live, delayed/EOD, and latest-reported data. Never invent unavailable metrics. Never reveal internal quant formulas; explain conclusions and evidence instead. You can discuss equities, indices, FX, metals, commodities, macro, fundamentals, earnings, filings, geopolitics, shipping, risk, market structure, and news-event transmission. When analyzing news, separate what is already released from expectations, explain hawkish/dovish/neutral implications, affected assets, confidence, conflicting evidence, and invalidation. If current information is missing, say so clearly."""

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

def _openrouter(message,ctx,key):
    model=os.getenv("OPENROUTER_MODEL","openrouter/free")
    payload={"model":model,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":f"NIGHT TERMINAL CONTEXT:\n{ctx}\n\nUSER QUESTION:\n{message}"}],"temperature":0.28,"max_tokens":1800}
    d=_post("https://openrouter.ai/api/v1/chat/completions",payload,{"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"https://night-terminal.vercel.app","X-Title":"NIGHT Terminal","User-Agent":"NIGHT-Terminal/1.0"})
    return (((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip(),model

def ask_luna(message:str,context:dict|None=None,credentials:dict|None=None):
    credentials=credentials or {};key=(credentials.get("openrouter_key") or os.getenv("OPENROUTER_API_KEY") or "").strip();ctx=json.dumps(context or {},ensure_ascii=False,default=str)[:18000]
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
