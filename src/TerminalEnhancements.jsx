import React,{useEffect,useMemo,useState}from'react';
import{createPortal}from'react-dom';
import{Newspaper,RefreshCw}from'lucide-react';

const API=import.meta.env.VITE_API_URL||'';
const FX_UNIVERSE=['XAUUSD','XAGUSD','EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD','NZDUSD','EURGBP','EURJPY','EURCHF','EURCAD','EURAUD','EURNZD','GBPJPY','GBPCHF','GBPCAD','GBPAUD','GBPNZD','AUDJPY','AUDCHF','AUDCAD','AUDNZD','NZDJPY','NZDCHF','NZDCAD','CADJPY','CADCHF','CHFJPY','BTCUSD','ETHUSD','NAS100','US30','SPX500'];
const NEWS_ASSETS=['XAUUSD','EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NAS100','SPX500','US30','BTCUSD'];
const credsLoad=()=>{try{return JSON.parse(localStorage.getItem('night_quant_creds')||'{}')}catch{return{}}};
const fmt=(v,d=1)=>v==null||Number.isNaN(Number(v))?'—':Number(v).toFixed(d);

async function post(path,body){const r=await fetch(API+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw new Error(j.detail||`API ${r.status}`);return j}
async function get(path){const r=await fetch(API+path);const j=await r.json();if(!r.ok)throw new Error(j.detail||`API ${r.status}`);return j}

export default function TerminalEnhancements(){
 const[open,setOpen]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[rows,setRows]=useState([]),[ai,setAi]=useState('');
 const creds=useMemo(credsLoad,[open]);
 useEffect(()=>{
  const apply=()=>{
   const sel=document.querySelector('.prodToolbar select');
   if(sel){const have=new Set([...sel.options].map(o=>o.value));FX_UNIVERSE.forEach(s=>{if(!have.has(s)){const o=document.createElement('option');o.value=s;o.textContent=s;sel.appendChild(o)}})}
   const aside=document.querySelector('.prodApp aside');
   if(aside&&!aside.querySelector('[data-news-prediction]')){const b=document.createElement('button');b.dataset.newsPrediction='1';b.innerHTML='<span style="font-size:16px">◈</span><span>News Prediction</span>';b.onclick=()=>setOpen(true);aside.appendChild(b)}
   const gem=document.querySelector('.prodKeys input[placeholder*="Gemini"]');if(gem)gem.style.display='none';
   document.querySelectorAll('.lunaHead p').forEach(p=>{if(p.textContent.includes('Gemini/OpenRouter'))p.textContent='AI market intelligence using OpenRouter + NIGHT terminal context.'});
  };
  apply();const mo=new MutationObserver(apply);mo.observe(document.body,{childList:true,subtree:true});return()=>mo.disconnect();
 },[]);
 async function run(){setBusy(true);setError('');setAi('');try{
   const baseNews=await Promise.all(NEWS_ASSETS.map(async s=>{try{return[s,await get(`/api/news/${s}`)]}catch{return[s,{articles:[],count:0}]}}));
   const mtfs=await Promise.all(NEWS_ASSETS.map(async s=>{try{return[s,await post('/api/analyse-mtf',{symbol:s,timeframe:'15m',credentials:creds})]}catch{return[s,{valid:false}]}}));
   const newsMap=Object.fromEntries(baseNews),mtfMap=Object.fromEntries(mtfs);
   const built=NEWS_ASSETS.map(s=>{const n=newsMap[s]||{},m=mtfMap[s]||{},score=Number(n.score||n.sentiment_score||0),impact=Number(n.impact_score||0),p=Number(m.probability_up||50);let newsDir=score>.08?'BULLISH':score<-.08?'BEARISH':'NEUTRAL';let tech=m.action==='LONG'?'BULLISH':m.action==='SHORT'?'BEARISH':'NEUTRAL';let aligned=newsDir==='NEUTRAL'||tech==='NEUTRAL'||newsDir===tech;let combined=aligned?(Math.abs(score)*35+Math.abs(p-50)*1.3+Number(m.agreement||0)*.35):(Math.abs(p-50)*.7+Number(m.agreement||0)*.2);let confidence=Math.max(20,Math.min(95,Math.round(combined)));let direction=newsDir==='NEUTRAL'?tech:aligned?newsDir:'MIXED';return{symbol:s,direction,newsDir,tech,confidence,impact,headlines:(n.articles||[]).slice(0,4),p,agreement:m.agreement||0,readiness:m.average_readiness||0,valid:m.valid}});
   setRows(built.sort((a,b)=>b.confidence-a.confidence));
   if(creds.openrouter_key){const context={generated_at:new Date().toISOString(),assets:built,headlines:Object.fromEntries(NEWS_ASSETS.map(s=>[s,(newsMap[s]?.articles||[]).slice(0,6)]))};const prompt='Create a concise institutional NEWS PREDICTION brief. For each highest-conviction asset explain expected directional impact, why, conflicting evidence, what would invalidate the view, and whether the news view aligns with technical MTF. Do not invent facts or guarantee outcomes. Prioritize actionable event transmission across USD, yields, gold, FX and US indices.';const j=await post('/api/luna',{message:prompt,context,credentials:creds});setAi(j.answer||'No AI response')}
  }catch(e){setError(e.message)}finally{setBusy(false)}}
 useEffect(()=>{if(open&&!rows.length)run()},[open]);
 if(!open)return null;
 return createPortal(<div className="newsPredictionOverlay"><div className="newsPredShell"><div className="newsPredHead"><div><small>NIGHT INTELLIGENCE</small><h1>NEWS PREDICTION & ANALYSIS</h1><p>Live headlines + current MTF technical state. Prediction is probabilistic, not a guarantee.</p></div><div><button onClick={run}><RefreshCw size={14}/>{busy?' ANALYZING…':' REFRESH'}</button><button onClick={()=>setOpen(false)}>CLOSE</button></div></div>{error&&<div className="prodError">{error}</div>}<div className="newsPredGrid">{rows.map((r,i)=><section key={r.symbol} className="newsPredCard"><div className="newsPredRank">#{i+1} NEWS OPPORTUNITY <b>{r.direction}</b></div><h2>{r.symbol}<strong>{r.confidence}%</strong></h2><div className="decisionGrid"><div><span>NEWS BIAS</span><b>{r.newsDir}</b></div><div><span>TECH MTF</span><b>{r.tech}</b></div><div><span>P↑</span><b>{fmt(r.p)}%</b></div><div><span>AGREEMENT</span><b>{fmt(r.agreement)}%</b></div><div><span>READINESS</span><b>{fmt(r.readiness)}%</b></div><div><span>IMPACT SCORE</span><b>{fmt(r.impact,2)}</b></div></div><div className="headlineStack">{r.headlines.map((h,j)=><article key={j}><b>{h.title||'Untitled headline'}</b><span>{h.source||h.domain||''}</span></article>)}</div></section>)}</div><section className="newsAiBrief"><h3>OPENROUTER AI — NEWS TRANSMISSION BRIEF</h3><pre>{ai|| (creds.openrouter_key?'Generating…':'Add OpenRouter key in Data Keys for AI narrative. Quant/news table works without it.')}</pre></section></div></div>,document.body)
}
