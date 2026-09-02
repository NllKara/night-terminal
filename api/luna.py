from __future__ import annotations
import json, os, urllib.request

SYSTEM="""You are Luna AI, the institutional market-intelligence assistant inside NIGHT Terminal. Answer naturally and directly. Use supplied NIGHT context as the primary source for prices, quant state, fundamentals, news, macro, geopolitics and shipping. Distinguish live, delayed/EOD, and latest-reported data. Never invent unavailable metrics. Never reveal internal quant formulas; explain conclusions and evidence instead. You can discuss equities, indices, FX, metals, commodities, macro, fundamentals, earnings, filings, geopolitics, shipping, risk and market structure. If current information is missing, say so clearly."""

def _post(url,payload,headers,timeout=45):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method="POST")
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())

def _openrouter(message,ctx,key):
    model=os.getenv("OPENROUTER_MODEL","openrouter/free")
    payload={"model":model,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":f"NIGHT TERMINAL CONTEXT:\n{ctx}\n\nUSER QUESTION:\n{message}"}],"temperature":0.3,"max_tokens":2200}
    d=_post("https://openrouter.ai/api/v1/chat/completions",payload,{"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"https://night-terminal.vercel.app","X-Title":"NIGHT Terminal","User-Agent":"NIGHT-Terminal/1.0"})
    return (((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip(),model

def ask_luna(message:str,context:dict|None=None,credentials:dict|None=None):
    credentials=credentials or {};key=(credentials.get("openrouter_key") or os.getenv("OPENROUTER_API_KEY") or "").strip();ctx=json.dumps(context or {},ensure_ascii=False,default=str)[:45000]
    if not key:return {"ok":False,"answer":"Open Data Keys and paste your OpenRouter API key to activate Luna AI.","model":None,"provider":"OpenRouter"}
    try:
        text,model=_openrouter(message,ctx,key)
        if text:return {"ok":True,"answer":text,"model":model,"provider":"OpenRouter"}
        return {"ok":False,"answer":"OpenRouter returned an empty response. Try again or check the free-model availability.","model":model,"provider":"OpenRouter"}
    except Exception as e:return {"ok":False,"answer":f"Luna could not reach OpenRouter ({type(e).__name__}). Check your key or free-tier limit.","model":None,"provider":"OpenRouter"}
