import React,{useState} from 'react';
import{createRoot}from'react-dom/client';
import{Activity,Brain,CandlestickChart,CalendarDays,ShieldAlert,Zap}from'lucide-react';
import'./style.css';

const API=import.meta.env.VITE_API_URL||'';
const initial={symbol:'XAUUSD',bias:'—',action:'RUN ANALYSIS',score:0,confidence:0,trade_readiness:0,greed:0,buyer_aggression:0,event_risk:0,volatility:0,data_quality:0,factors:{}};

function Meter({name,value}){
  return <div className="meter"><div><span>{name}</span><b>{value??0}%</b></div><i><em style={{width:`${value??0}%`}}/></i></div>
}

function App(){
  const[symbol,setSymbol]=useState('XAUUSD');
  const[tf,setTf]=useState('5m');
  const[data,setData]=useState(initial);
  const[loading,setLoading]=useState(false);
  const[error,setError]=useState('');

  async function run(){
    setLoading(true);setError('');
    try{
      const r=await fetch(`${API}/api/analyse`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol,timeframe:tf})});
      if(!r.ok)throw new Error(`Analysis API returned ${r.status}`);
      setData(await r.json());
    }catch(e){setError(e.message||'Analysis failed');}
    finally{setLoading(false)}
  }

  return <main>
    <header><div className="brand"><Brain/><div><strong>NIGHT</strong><small>AI MARKET INTELLIGENCE</small></div></div><div className="live"><span/>ENGINE ONLINE</div></header>
    <section className="toolbar">
      <select value={symbol} onChange={e=>setSymbol(e.target.value)}>{['XAUUSD','EURUSD','GBPUSD','USDJPY','BTCUSD','NAS100','US30'].map(x=><option key={x}>{x}</option>)}</select>
      <select value={tf} onChange={e=>setTf(e.target.value)}>{['1m','5m','15m','1h','4h','1D'].map(x=><option key={x}>{x}</option>)}</select>
      <button onClick={run} disabled={loading}><Zap size={17}/>{loading?'ANALYSING…':'RUN FULL ANALYSIS'}</button>
    </section>
    {error&&<div className="error">{error}</div>}
    <section className="hero"><div><small>COMPOSITE MARKET BIAS</small><h1>{data.bias}</h1><p>{data.symbol} · {data.timeframe||tf}</p></div><div className="score"><strong>{data.score}</strong><span>/100</span></div><div className="decision"><small>EXECUTION STATE</small><b>{data.action}</b><p>Confidence {data.confidence}%</p></div></section>
    <section className="grid">
      <article><h3><Activity/>Market Intelligence</h3><Meter name="Trade Readiness" value={data.trade_readiness}/><Meter name="Buyer Aggression" value={data.buyer_aggression}/><Meter name="Greed / Momentum" value={data.greed}/><Meter name="Volatility" value={data.volatility}/></article>
      <article><h3><CandlestickChart/>Factor Matrix</h3>{Object.entries(data.factors||{}).map(([k,v])=><Meter key={k} name={k.replace('_',' ')} value={v}/>)}</article>
      <article><h3><ShieldAlert/>Risk Engine</h3><Meter name="Event Risk" value={data.event_risk}/><Meter name="Data Quality" value={data.data_quality}/><div className="note"><b>Scenario</b><p>{data.scenario||'Run analysis to build the market scenario.'}</p><b>Invalidation</b><p>{data.invalidation||'—'}</p></div></article>
    </section>
    <section className="bottom"><div><CalendarDays/><span>ECONOMIC CALENDAR</span><b>Provider-ready</b></div><div><Brain/><span>MACRO + INTERMARKET</span><b>Scored</b></div><div><Activity/><span>VOLUME + AGGRESSION</span><b>Scored</b></div></section>
    <footer>Decision-support only · Scores must be calibrated against real historical/live data before relying on them.</footer>
  </main>
}

createRoot(document.getElementById('root')).render(<App/>);
