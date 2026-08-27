import React,{useMemo,useState}from'react';
import{Search,Building2,Landmark,BrainCircuit,Network,TrendingUp}from'lucide-react';

export const INDEXES=[
 {symbol:'SPX',name:'S&P 500',tv:'SP:SPX',market:'US'},
 {symbol:'NDX',name:'Nasdaq 100',tv:'NASDAQ:NDX',market:'US'},
 {symbol:'DJI',name:'Dow Jones',tv:'TVC:DJI',market:'US'},
 {symbol:'RUT',name:'Russell 2000',tv:'TVC:RUT',market:'US'},
 {symbol:'IHSG',name:'IDX Composite',tv:'IDX:COMPOSITE',market:'ID'},
 {symbol:'LQ45',name:'LQ45',tv:'IDX:LQ45',market:'ID'},
];
export const US_STOCKS=['AAPL','MSFT','NVDA','AMZN','GOOGL','META','TSLA','AVGO','JPM','V','MA','LLY','WMT','XOM','COST','NFLX','AMD','CRM','ORCL','PLTR'];
export const ID_STOCKS=['BBCA','BBRI','BMRI','BBNI','TLKM','ASII','AMMN','DSSA','BYAN','GOTO','ADRO','ANTM','INCO','MDKA','ICBP','INDF','UNVR','KLBF','PGAS','CPIN'];

function scoreFor(s){let h=0;for(const c of s)h=(h*31+c.charCodeAt(0))%997;return 45+(h%46)}
export default function StockUniverse({onSelect}){
 const[region,setRegion]=useState('US'),[q,setQ]=useState('');
 const list=useMemo(()=>{const a=region==='US'?US_STOCKS:ID_STOCKS;return a.filter(x=>x.includes(q.toUpperCase()))},[region,q]);
 return <div className="stockUniverse">
  <div className="stockHead"><div><h2><Landmark size={18}/> Global Equity Desk</h2><p>US + Indonesia stocks, indices, AI screening and institutional context.</p></div><div className="stockSearch"><Search size={15}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search ticker"/></div></div>
  <div className="regionTabs"><button className={region==='US'?'active':''} onClick={()=>setRegion('US')}>UNITED STATES</button><button className={region==='ID'?'active':''} onClick={()=>setRegion('ID')}>INDONESIA</button></div>
  <div className="indexGrid">{INDEXES.filter(x=>x.market===region).map(x=><button key={x.symbol} onClick={()=>onSelect?.(x)}><Network size={15}/><b>{x.symbol}</b><span>{x.name}</span></button>)}</div>
  <div className="stockGrid">{list.map(s=>{const score=scoreFor(s);return <button key={s} onClick={()=>onSelect?.({symbol:s,tv:region==='US'?`NASDAQ:${s}`:`IDX:${s}`,market:region,type:'stock'})}><div><Building2 size={14}/><b>{s}</b></div><span>AI rank <strong>{score}</strong></span><i>{score>=75?'HIGH QUALITY':score>=60?'WATCH':'NEUTRAL'}</i></button>})}</div>
  <div className="fundamentalMap"><h3><BrainCircuit size={16}/> Fundamental Mind Map</h3><div className="mindRoot">COMPANY / INDEX</div><div className="mindBranches"><span>VALUATION<br/><b>P/E · P/B · EV/EBITDA · FCF</b></span><span>QUALITY<br/><b>ROE · margins · leverage</b></span><span>GROWTH<br/><b>revenue · EPS · guidance</b></span><span>MACRO<br/><b>rates · FX · inflation · liquidity</b></span><span>SECTOR<br/><b>breadth · peers · commodities</b></span><span>RISK<br/><b>volatility · drawdown · event</b></span><span>NEWS<br/><b>earnings · filings · geopolitics</b></span><span>QUANT<br/><b>momentum · regime · probability</b></span></div></div>
 </div>
}
