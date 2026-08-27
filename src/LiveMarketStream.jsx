import React,{useEffect,useRef,useState}from'react';

const TD_MAP={XAUUSD:'XAU/USD',EURUSD:'EUR/USD',GBPUSD:'GBP/USD',USDJPY:'USD/JPY',NAS100:'NDX',US30:'DJI'};
const TF_MS={'1m':60000,'5m':300000,'15m':900000,'1h':3600000,'4h':14400000,'1D':86400000};

export default function LiveMarketStream({symbol,timeframe='5m',apiKey,credentials={},apiBase='',onPrice,onQuant}){
 const[status,setStatus]=useState('CONNECTING'),[price,setPrice]=useState(null),[last,setLast]=useState(null),[latency,setLatency]=useState(null),[barsReady,setBarsReady]=useState(0);
 const wsRef=useRef(null),barsRef=useRef([]),timerRef=useRef(null),lastQuantRef=useRef(0),priceRef=useRef(null);
 useEffect(()=>{
  let alive=true,heartbeat=null;
  setStatus('CONNECTING');setPrice(null);setLast(null);setLatency(null);setBarsReady(0);priceRef.current=null;barsRef.current=[];
  onQuant?.({last_price:null,realtime_price:false,live_symbol:symbol,source:'Waiting for live '+symbol+' feed'});
  const tfms=TF_MS[timeframe]||300000;
  const post=async(path,body)=>{const r=await fetch(`${apiBase}${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw new Error(`API ${r.status}`);return r.json()};
  const seed=async()=>{try{const j=await post('/api/bars',{symbol,timeframe,credentials});barsRef.current=(j.bars||[]).slice(-220).map(b=>({...b,volume:Number(b.volume||0)}));setBarsReady(barsRef.current.length)}catch{barsRef.current=[];setBarsReady(0)}};
  const analyseNow=async(source,volumeType)=>{if(!alive||barsRef.current.length<30)return;const now=Date.now();if(now-lastQuantRef.current<2500)return;lastQuantRef.current=now;try{const j=await post('/api/analyse-bars',{symbol,timeframe,bars:barsRef.current.slice(-220),credentials,source,volume_type:volumeType});if(alive)onQuant?.({...j,realtime_price:true,live_symbol:symbol})}catch{}};
  const ingest=(p,ts,qty=1,source='Twelve Data WebSocket',volumeType='tick volume')=>{
    if(!alive||!Number.isFinite(p))return;
    const eventMs=ts?(Number(ts)>1e12?Number(ts):Number(ts)*1000):Date.now();
    const prev=priceRef.current;priceRef.current=p;setLast(prev);setPrice(p);setLatency(Math.max(0,Date.now()-eventMs));setStatus('LIVE');onPrice?.(p,eventMs);
    // Reference/Execution price is overwritten immediately by the active symbol's live tick.
    onQuant?.({last_price:p,realtime_price:true,live_symbol:symbol,source,volume_type:volumeType});
    const bucket=Math.floor(eventMs/tfms)*tfms;const bars=barsRef.current;let b=bars[bars.length-1];
    // Reject cross-instrument/stale seeds. If the historical tail is wildly different from the live quote,
    // do not let it contaminate execution or quant outputs.
    if(b&&Number(b.close)>0&&Math.abs(p/Number(b.close)-1)>0.035){barsRef.current=[];bars.length=0;b=null;setBarsReady(0)}
    if(!b||Number(b.time)!==bucket){b={time:bucket,open:p,high:p,low:p,close:p,volume:Math.max(0,Number(qty)||1)};bars.push(b);if(bars.length>240)bars.shift()}
    else{b.high=Math.max(Number(b.high),p);b.low=Math.min(Number(b.low),p);b.close=p;b.volume=Number(b.volume||0)+Math.max(0,Number(qty)||1)}
    setBarsReady(bars.length);clearTimeout(timerRef.current);timerRef.current=setTimeout(()=>analyseNow(source,volumeType),450);
  };
  (async()=>{
   await seed();
   try{
    if(symbol==='BTCUSD'){
      const ws=new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@trade');wsRef.current=ws;
      ws.onopen=()=>alive&&setStatus('LIVE');
      ws.onmessage=e=>{try{const j=JSON.parse(e.data);ingest(Number(j.p),j.T,Number(j.q||0),'Binance realtime trade stream','exchange traded BTC volume')}catch{}};
      ws.onerror=()=>alive&&setStatus('STREAM ERROR');ws.onclose=()=>alive&&setStatus('OFFLINE');
    }else if(apiKey&&TD_MAP[symbol]){
      const ws=new WebSocket(`wss://ws.twelvedata.com/v1/quotes/price?apikey=${encodeURIComponent(apiKey)}`);wsRef.current=ws;
      ws.onopen=()=>{setStatus('SUBSCRIBING');ws.send(JSON.stringify({action:'subscribe',params:{symbols:TD_MAP[symbol]}}));heartbeat=setInterval(()=>{try{ws.send(JSON.stringify({action:'heartbeat'}))}catch{}},10000)};
      ws.onmessage=e=>{try{const j=JSON.parse(e.data);if(j.event==='price'&&j.symbol===TD_MAP[symbol])ingest(Number(j.price),j.timestamp,1,'Twelve Data realtime WebSocket','tick volume');else if(j.event==='subscribe-status'&&j.status==='error')setStatus('PLAN LIMIT')}catch{}};
      ws.onerror=()=>alive&&setStatus('STREAM ERROR');ws.onclose=()=>alive&&setStatus('OFFLINE');
    }else setStatus('CHART LIVE / ADD KEY');
   }catch{setStatus('STREAM ERROR')}
  })();
  return()=>{alive=false;if(heartbeat)clearInterval(heartbeat);clearTimeout(timerRef.current);try{wsRef.current?.close()}catch{}};
 },[symbol,timeframe,apiKey]);
 const dir=price!=null&&last!=null?(price>last?'up':price<last?'down':'flat'):'flat';
 return <div className={`liveStream ${status==='LIVE'?'ok':''}`}><span className="liveDot"/><b>{status}</b><strong className={dir}>{price==null?'—':Number(price).toLocaleString(undefined,{maximumFractionDigits:5})}</strong>{latency!=null&&status==='LIVE'&&<small>{latency}ms · {barsReady} bars</small>}</div>
}
