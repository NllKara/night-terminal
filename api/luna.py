from __future__ import annotations
import json, os, urllib.request

def ask_luna(message:str, context:dict|None=None):
    key=os.getenv("OPENAI_API_KEY")
    if not key:
        return {"ok":False,"answer":"Luna AI is not connected yet. Add OPENAI_API_KEY in Vercel Environment Variables, then redeploy.","model":None}
    model=os.getenv("OPENAI_MODEL","gpt-5")
    ctx=json.dumps(context or {},ensure_ascii=False)[:24000]
    payload={
        "model":model,
        "store":False,
        "tools":[{"type":"web_search"}],
        "instructions":"You are Luna AI, the institutional market intelligence assistant inside NIGHT Terminal. Answer naturally, directly, and intelligently. Use the supplied live terminal context first. When the question needs current public information, use web search. Distinguish live market prices from delayed/EOD prices and latest-reported fundamentals. Do not invent unavailable metrics. Never reveal internal quant formulas; explain conclusions and evidence instead. You can discuss macro, fundamentals, equities, FX, commodities, geopolitics, shipping, earnings, filings, risk, and market structure.",
        "input":f"TERMINAL CONTEXT:\n{ctx}\n\nUSER QUESTION:\n{message}"
    }
    req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode(),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","User-Agent":"NIGHT-Terminal/1.0"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=45) as r:d=json.loads(r.read().decode())
        text=d.get("output_text")
        if not text:
            parts=[]
            for item in d.get("output") or []:
                for c in item.get("content") or []:
                    if c.get("type")=="output_text" and c.get("text"):parts.append(c["text"])
            text="\n".join(parts)
        return {"ok":True,"answer":text or "Luna returned no text.","model":model}
    except Exception as e:
        return {"ok":False,"answer":f"Luna AI request failed: {type(e).__name__}","model":model}
