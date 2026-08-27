from __future__ import annotations
import json, os, urllib.request

SYSTEM="""You are Luna AI, the institutional market-intelligence assistant inside NIGHT Terminal. Answer naturally and directly. Use supplied terminal context as the primary source for prices, quant state, fundamentals, news, macro, geopolitics and shipping. Distinguish LIVE, delayed/EOD, and latest-reported data. Never invent unavailable metrics. Never reveal internal quant formulas; explain conclusions and evidence instead. You can discuss equities, indices, FX, metals, commodities, macro, fundamentals, earnings, filings, geopolitics, shipping, risk and market structure. If context does not contain current information, say that clearly rather than pretending it is live."""

def _post(url,payload,headers,timeout=45):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method="POST")
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())

def _gemini(message,ctx,key):
    model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload={"system_instruction":{"parts":[{"text":SYSTEM}]},"contents":[{"role":"user","parts":[{"text":f"TERMINAL CONTEXT:\n{ctx}\n\nUSER QUESTION:\n{message}"}]}],"generationConfig":{"temperature":0.35,"maxOutputTokens":1800}}
    d=_post(url,payload,{"Content-Type":"application/json","User-Agent":"NIGHT-Terminal/1.0"})
    parts=[]
    for cand in d.get("candidates") or []:
        for p in ((cand.get("content") or {}).get("parts") or []):
            if p.get("text"):parts.append(p["text"])
    return "\n".join(parts).strip(),model

def _openrouter(message,ctx,key):
    model=os.getenv("OPENROUTER_MODEL","openrouter/free")
    payload={"model":model,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":f"TERMINAL CONTEXT:\n{ctx}\n\nUSER QUESTION:\n{message}"}],"temperature":0.35,"max_tokens":1800}
    d=_post("https://openrouter.ai/api/v1/chat/completions",payload,{"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"https://night-terminal.vercel.app","X-Title":"NIGHT Terminal","User-Agent":"NIGHT-Terminal/1.0"})
    text=(((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    return text,model

def ask_luna(message:str,context:dict|None=None,credentials:dict|None=None):
    ctx=json.dumps(context or {},ensure_ascii=False,default=str)[:30000]
    credentials=credentials or {}
    gemini=(credentials.get("gemini_key") or os.getenv("GEMINI_API_KEY") or "").strip()
    router=(credentials.get("openrouter_key") or os.getenv("OPENROUTER_API_KEY") or "").strip()
    errors=[]
    if gemini:
        try:
            text,model=_gemini(message,ctx,gemini)
            if text:return {"ok":True,"answer":text,"model":model,"provider":"Gemini"}
        except Exception as e:errors.append("Gemini "+type(e).__name__)
    if router:
        try:
            text,model=_openrouter(message,ctx,router)
            if text:return {"ok":True,"answer":text,"model":model,"provider":"OpenRouter Free"}
        except Exception as e:errors.append("OpenRouter "+type(e).__name__)
    if not gemini and not router:
        return {"ok":False,"answer":"Open Data Keys in NIGHT and paste a Gemini API key or OpenRouter API key to activate Luna AI.","model":None,"provider":None}
    return {"ok":False,"answer":"Luna could not reach the configured free AI provider. "+(" / ".join(errors) if errors else "Check the key and free-tier limit."),"model":None,"provider":None}
