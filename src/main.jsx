import React,{useEffect,useMemo,useState}from'react';
import{createRoot}from'react-dom/client';
import{Activity,Brain,CalendarDays,ChartNoAxesCombined,Database,Flame,Gauge,Globe2,History,KeyRound,Layers3,MessageSquare,RefreshCw,ScanSearch,ShieldAlert,Target,Zap}from'lucide-react';
import TradingViewChart from'./TradingViewChart';
import'./style.css';

const API=import.meta.env.VITE_API_URL||'';
const symbols=['XAUUSD','EURUSD','GBPUSD','USDJPY','BTCUSD','NAS100','US30'];
const tfMap={'1m':'1','5m':'5','15m':'15','1h':'60','4h':'240','1D':'D'};
const timeframes=['1m','5m','15m','1h','4h','1D'];
const zero={symbol:'XAUUSD',valid:false,bias:'—',action:'CONNECT DATA',score:50,confidence:0,trade_readiness:0,greed:50,buyer_aggression:50,seller_aggression:50,event_risk:0,volatility:0,data_quality:0,components:{},math:{},volume_profile:{}};

function Meter({name,value,centered=false}){const v=Number(value||0);const width=centered?Math.min(100,Math.abs(v)*100):Math.max(0,Math.min(100,v));return <div className="meter"><div><span>{name}</span><b>{centered?(v>=0?'+':'')+v.toFixed(3):Math.round(v)+'%'}</b></div><i><em style={{width:`${width}%`}}/></i></div>}
function Pill({children,tone=''}){return <span className={`pill ${tone}`}>{children}</span>}
function Card({title,icon:Icon,children,className=''}){return <section className={`card ${className}`}><h3>{Icon&&<Icon size={15}/>} {title}</h3>{children}</section>}
function fmt(v,d=3){return v==null?'—':Number(v).toFixed(d)}
function loadCreds(){try{return JSON.parse(localStorage.getItem('night_quant_creds')||'{}')}catch{return{}}}

function App(){
 const[symbol,setSymbol]=useState('XAUUSD'),[tf,setTf]=useState('5m'),[data,setData]=useState(zero),[loading,setLoading]=useState(false),[tab,setTab]=useState('terminal'),[error,setError]=useState('');
 const[creds,setCreds]=useState(loadCreds),[showKeys,setShowKeys]=useState(false),[chat,setChat]=useState([{role:'bot',text:'Quant Chat ready. Ask: why bias, volume, aggression, formula, entry, SL, TP.'}]),[msg,setMsg]=useState('');
 const components=data.components||{},math=data.math||{},vp=data.volume_profile||{};
 const hasKey=Boolean(creds.twelve_key||creds.oanda_token);

 async function run(){
  setLoading(true);setError('');
  try{
   const r=await fetch(`${API}/api/analyse`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol,timeframe:tf,credentials:creds})});
   const j=await r.json();if(!r.ok)throw new Error(j.detail||`API ${r.status}`);setData(j);
  }catch(e){setError(e.message||'Analysis failed')}finally{setLoading(false)}
 }
 function saveCreds(){localStorage.setItem('night_quant_creds',JSON.stringify(creds));setShowKeys(false);run()}
 async function sendChat(){const q=msg.trim();if(!q)return;setChat(x=>[...x,{role:'me',text:q}]);setMsg('');try{const r=await fetch(`${API}/api/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q,analysis:data})});const j=await r.json();setChat(x=>[...x,{role:'bot',text:j.answer||'No answer'}])}catch{setChat(x=>[...x,{role:'bot',text:'Chat API error.'}])}}
 useEffect(()=>{run()},[]);

 const actionTone=data.action==='LONG'?'good':data.action==='SHORT'?'bad':data.action==='WAIT'?'warn':'';
 const probUp=data.probability_up??50,probDn=data.probability_down??50;
 const sourceOk=data.valid;
 const mtf=useMemo(()=>timeframes.map((x,i)=>({tf:x,bias:i===2?data.bias:'CALCULATE',score:i===2?data.score:'—'})),[data]);

 return <div className="app">
  <aside><div className="logo"><Brain/><b>NIGHT</b><small>QUANT</small></div>{[['terminal',ChartNoAxesCombined,'Command'],['quant',Gauge,'Quant Lab'],['chat',MessageSquare,'Quant Chat'],['scanner',ScanSearch,'Scanner'],['macro',Globe2,'Macro'],['calendar',CalendarDays,'Calendar'],['journal',History,'Journal'],['data',Database,'Data Center']].map(([id,I,l])=><button key={id} className={tab===id?'active':''} onClick={()=>setTab(id)}><I size={16}/><span>{l}</span></button>)}</aside>
  <main>
   <header><div><small>PERSONAL QUANT MARKET INTELLIGENCE</small><h1>{symbol} <Pill tone={sourceOk?'live':'warn'}>{sourceOk?'QUANT LIVE':'DATA REQUIRED'}</Pill></h1></div><div className="headeractions"><button className="ghost" onClick={()=>setShowKeys(v=>!v)}><KeyRound size={14}/> Data Keys</button><div className="status"><span/>ENGINE ONLINE</div></div></header>
   <div className="toolbar"><select value={symbol} onChange={e=>setSymbol(e.target.value)}>{symbols.map(x=><option key={x}>{x}</option>)}</select><select value={tf} onChange={e=>setTf(e.target.value)}>{timeframes.map(x=><option key={x}>{x}</option>)}</select><button onClick={run} disabled={loading}><Zap size={16}/>{loading?'CALCULATING…':'RUN QUANT ANALYSIS'}</button></div>
   {showKeys&&<div className="keys"><b>FREE DATA SETUP</b><p>For XAU/FX: OANDA practice is best for tick-volume. Twelve Data Basic can provide free real-time FX/crypto REST. BTCUSD works from Binance without key.</p><input placeholder="Twelve Data API key" value={creds.twelve_key||''} onChange={e=>setCreds({...creds,twelve_key:e.target.value})}/><input placeholder="OANDA practice account ID" value={creds.oanda_account||''} onChange={e=>setCreds({...creds,oanda_account:e.target.value})}/><input type="password" placeholder="OANDA practice token" value={creds.oanda_token||''} onChange={e=>setCreds({...creds,oanda_token:e.target.value})}/><button onClick={saveCreds}>SAVE LOCALLY + ANALYSE</button><small>Keys are stored in your browser localStorage and sent only to your own API route for requests. Never commit keys to GitHub.</small></div>}
   {error&&<div className="error">{error}</div>}
   {!data.valid&&<div className="setupbanner"><b>No real OHLCV yet.</b><span>{symbol==='BTCUSD'?'BTC should load from Binance public data automatically. Re-run analysis.':'Open Data Keys and connect a free OANDA practice feed or Twelve Data key. Quant engine refuses to fabricate market numbers.'}</span>{data.provider_errors?.length>0&&<code>{data.provider_errors.join(' · ')}</code>}</div>}

   {tab==='terminal'&&<>
    <div className="hero"><div><small>QUANT BIAS</small><strong>{data.bias}</strong><span>Latent score {fmt(data.score,2)}/100</span></div><div><small>EXECUTION</small><strong className={actionTone}>{data.action}</strong><span>Readiness {fmt(data.trade_readiness,1)}%</span></div><div><small>PROBABILITY</small><strong>{fmt(probUp,1)}%</strong><span>Up vs {fmt(probDn,1)}% Down</span></div><div><small>EXPECTED VALUE</small><strong>{data.bias==='BEARISH'?fmt(data.ev_short_r):fmt(data.ev_long_r)}R</strong><span>1.5R canonical payoff</span></div></div>
    <div className="workspace"><div className="chartcol"><Card title="TradingView Live Chart" icon={ChartNoAxesCombined} className="chartcard"><TradingViewChart symbol={symbol} interval={tfMap[tf]}/></Card><div className="row3">
      <Card title="Real Volume Profile" icon={Layers3}><div className="vp"><div>VAH <b>{fmt(vp.vah,3)}</b></div><div className="poc">POC <b>{fmt(vp.poc,3)}</b></div><div>VAL <b>{fmt(vp.val,3)}</b></div></div><p className="muted">Source: {data.source||'—'}<br/>Volume: {data.volume_type||'—'}</p></Card>
      <Card title="Aggression / Flow" icon={Flame}><Meter name="Buyer aggression" value={data.buyer_aggression}/><Meter name="Seller aggression" value={data.seller_aggression}/><div className="kv"><span>Signed pressure</span><b>{fmt(math.signed_volume_pressure)}</b></div><div className="kv"><span>Volume z</span><b>{fmt(math.volume_z,2)}</b></div></Card>
      <Card title="Probability / Risk" icon={Target}><Meter name="P(up)" value={probUp}/><Meter name="P(down)" value={probDn}/><div className="kv"><span>EV long</span><b>{fmt(data.ev_long_r)}R</b></div><div className="kv"><span>EV short</span><b>{fmt(data.ev_short_r)}R</b></div></Card>
     </div></div>
     <div className="sidecol"><Card title="Quant State" icon={Activity}><div className="kv"><span>Regime</span><b>{data.regime||'—'}</b></div><div className="kv"><span>Confidence</span><b>{fmt(data.confidence,1)}%</b></div><div className="kv"><span>Conflict</span><b>{fmt(data.conflict,1)}%</b></div><div className="kv"><span>Data quality</span><b>{fmt(data.data_quality,1)}%</b></div></Card><Card title="Factor Edge [-1,+1]" icon={Gauge}>{Object.entries(components).map(([k,v])=><Meter key={k} name={k} value={v} centered/>)}</Card><Card title="Multi-Timeframe" icon={RefreshCw}>{mtf.map(x=><div className="mtf" key={x.tf}><b>{x.tf}</b><span>{x.score}</span><Pill>{x.bias}</Pill></div>)}<small className="muted">Exact MTF quant is next: each timeframe will be separately fetched/calculated, not synthetically shifted.</small></Card></div></div>
    <div className="row4"><Card title="Quant Thesis" icon={Brain}><p>{data.scenario||data.reason||'Connect market data.'}</p><b>Invalidation</b><p>{data.invalidation||'—'}</p></Card><Card title="Volume + Trend Math" icon={Gauge}><div className="kv"><span>Momentum z</span><b>{fmt(math.momentum_z)}</b></div><div className="kv"><span>Trend t-stat</span><b>{fmt(math.trend_t_stat)}</b></div><div className="kv"><span>R²</span><b>{fmt(math.trend_r2)}</b></div><div className="kv"><span>Kaufman ER</span><b>{fmt(math.efficiency_ratio)}</b></div></Card><Card title="Volatility Math" icon={ShieldAlert}><div className="kv"><span>Realized vol</span><b>{fmt(math.realized_vol,5)}</b></div><div className="kv"><span>ATR %</span><b>{fmt((math.atr_pct||0)*100,3)}%</b></div><div className="kv"><span>ATR z</span><b>{fmt(math.atr_z)}</b></div><Meter name="Volatility state" value={data.volatility}/></Card><Card title="Data Provenance" icon={Database}><p><b>{data.source||'No provider'}</b></p><p>{data.volume_type||'No volume'}</p><Pill tone={data.valid?'good':'bad'}>{data.valid?'CALCULATED FROM REAL BARS':'NO FABRICATED DATA'}</Pill></Card></div>
   </>}

   {tab==='quant'&&<><Card title="Quant Formula Engine" icon={Gauge}><div className="formula">{data.formula||'Connect data to calculate.'}</div></Card><div className="row3"><Card title="Raw Statistics" icon={Activity}>{Object.entries(math).map(([k,v])=><div className="kv" key={k}><span>{k.replaceAll('_',' ')}</span><b>{fmt(v,5)}</b></div>)}</Card><Card title="Weighted Components" icon={Layers3}>{Object.entries(components).map(([k,v])=><div className="kv" key={k}><span>{k}</span><b>{fmt(v,4)}</b></div>)}</Card><Card title="Outputs" icon={Target}><div className="kv"><span>Latent edge</span><b>{fmt(data.edge,4)}</b></div><div className="kv"><span>P up</span><b>{fmt(probUp,2)}%</b></div><div className="kv"><span>P down</span><b>{fmt(probDn,2)}%</b></div><div className="kv"><span>EV long</span><b>{fmt(data.ev_long_r,3)}R</b></div><div className="kv"><span>EV short</span><b>{fmt(data.ev_short_r,3)}R</b></div></Card></div></>}

   {tab==='chat'&&<Card title="Quant Chat" icon={MessageSquare} className="chatcard"><div className="chatlog">{chat.map((x,i)=><div key={i} className={`bubble ${x.role}`}>{x.text}</div>)}</div><div className="chatinput"><input value={msg} onChange={e=>setMsg(e.target.value)} onKeyDown={e=>e.key==='Enter'&&sendChat()} placeholder="Ask: kenapa bullish? buyer winning? formula? entry SL TP?"/><button onClick={sendChat}>SEND</button></div></Card>}

   {tab==='scanner'&&<Card title="Opportunity Scanner" icon={ScanSearch}><p className="muted">Scanner will only rank symbols after each has real provider data. No fake generated scores.</p><table><thead><tr><th>Market</th><th>Data</th><th>Quant status</th></tr></thead><tbody>{symbols.map(s=><tr key={s}><td>{s}</td><td>{s==='BTCUSD'?'Binance public':hasKey?'Provider configured':'Needs free key/feed'}</td><td>{s===symbol&&data.valid?`${data.action} · ${fmt(data.trade_readiness,1)}%`:'Run calculation'}</td></tr>)}</tbody></table></Card>}

   {tab==='macro'&&<div className="row3"><Card title="Macro Engine" icon={Globe2}><p>FRED connector planned for rates/inflation/labor data. Macro score is deliberately neutral until sourced; the quant engine does not invent a macro view.</p></Card><Card title="Intermarket" icon={Activity}><p>DXY, US yields, real yields, silver, VIX and index returns will be transformed to rolling z-scores/correlations and fed into the latent edge.</p></Card><Card title="Current Contribution" icon={Brain}><div className="kv"><span>Macro</span><b>{fmt(components.macro)}</b></div><div className="kv"><span>Intermarket</span><b>{fmt(components.intermarket)}</b></div></Card></div>}
   {tab==='calendar'&&<Card title="Economic Calendar" icon={CalendarDays}><p>Chart/calendar display can be embedded immediately; quant event-surprise scoring needs a real calendar provider. Until then event risk is not fabricated.</p></Card>}
   {tab==='journal'&&<div className="row3"><Card title="Journal" icon={History}><p>Trade storage + MAE/MFE + setup outcome dataset comes next.</p></Card><Card title="Calibration" icon={Activity}><p>Future calibration: predicted probability buckets vs realized direction, Brier score, hit-rate and EV by regime.</p></Card><Card title="Mistake Detector" icon={ShieldAlert}><p>Will compare entry timing against model state and post-trade MFE/MAE instead of judging only win/loss.</p></Card></div>}
   {tab==='data'&&<Card title="Data Center" icon={Database}><table><thead><tr><th>Asset</th><th>Free source</th><th>Volume type</th><th>Use</th></tr></thead><tbody><tr><td>XAU / FX</td><td>OANDA practice</td><td>Tick volume</td><td>Quant OHLCV + VP/flow proxy</td></tr><tr><td>FX / crypto</td><td>Twelve Data Basic</td><td>Provider-dependent</td><td>Real-time REST bars</td></tr><tr><td>BTCUSD</td><td>Binance public</td><td>True exchange volume</td><td>Quant OHLCV</td></tr><tr><td>Macro</td><td>FRED</td><td>n/a</td><td>Rates/inflation/labor</td></tr></tbody></table></Card>}
   <footer>Quant decision-support. No number is invented when a provider is missing. Spot FX/CFD has no centralized exchange volume; terminal labels tick-volume and exchange-volume separately.</footer>
  </main>
 </div>
}
createRoot(document.getElementById('root')).render(<App/>);
