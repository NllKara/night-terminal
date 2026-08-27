import React,{useEffect,useRef,useState}from'react';

const TD_MAP={
 XAUUSD:'XAU/USD',EURUSD:'EUR/USD',GBPUSD:'GBP/USD',USDJPY:'USD/JPY',
 NAS100:'NDX',US30:'DJI'
};

export default function LiveMarketStream({symbol,apiKey,onPrice}){
 const[status,setStatus]=useState('CONNECTING');
 const[price,setPrice]=useState(null);
 const[last,setLast]=useState(null);
 const[latency,setLatency]=useState(null);
 const wsRef=useRef(null);
 useEffect(()=>{
  let alive=true,heartbeat=null;
  const setTick=(p,ts)=>{if(!alive||!Number.isFinite(p))return;setLast(price);setPrice(p);if(ts){const t=Number(ts)>1e12?Number(ts):Number(ts)*1000;setLatency(Math.max(0,Date.now()-t))}setStatus('LIVE');onPrice?.(p,ts)};
  try{
   if(symbol==='BTCUSD'){
    const ws=new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@trade');wsRef.current=ws;
    ws.onopen=()=>alive&&setStatus('LIVE');
    ws.onmessage=e=>{try{const j=JSON.parse(e.data);setTick(Number(j.p),j.T)}catch{}};
    ws.onerror=()=>alive&&setStatus('STREAM ERROR');ws.onclose=()=>alive&&setStatus('OFFLINE');
   }else if(apiKey&&TD_MAP[symbol]){
    const ws=new WebSocket(`wss://ws.twelvedata.com/v1/quotes/price?apikey=${encodeURIComponent(apiKey)}`);wsRef.current=ws;
    ws.onopen=()=>{setStatus('SUBSCRIBING');ws.send(JSON.stringify({action:'subscribe',params:{symbols:TD_MAP[symbol]}}));heartbeat=setInterval(()=>{try{ws.send(JSON.stringify({action:'heartbeat'}))}catch{}},10000)};
    ws.onmessage=e=>{try{const j=JSON.parse(e.data);if(j.event==='price'&&j.symbol===TD_MAP[symbol])setTick(Number(j.price),j.timestamp);else if(j.event==='subscribe-status'&&j.status==='error')setStatus('PLAN LIMIT')}catch{}};
    ws.onerror=()=>alive&&setStatus('STREAM ERROR');ws.onclose=()=>alive&&setStatus('OFFLINE');
   }else setStatus('CHART LIVE / ADD KEY');
  }catch{setStatus('STREAM ERROR')}
  return()=>{alive=false;if(heartbeat)clearInterval(heartbeat);try{wsRef.current?.close()}catch{}};
 },[symbol,apiKey]);
 const dir=price!=null&&last!=null?(price>last?'up':price<last?'down':'flat'):'flat';
 return <div className={`liveStream ${status==='LIVE'?'ok':''}`}><span className="liveDot"/><b>{status}</b><strong className={dir}>{price==null?'—':Number(price).toLocaleString(undefined,{maximumFractionDigits:5})}</strong>{latency!=null&&status==='LIVE'&&<small>{latency}ms</small>}</div>
}
