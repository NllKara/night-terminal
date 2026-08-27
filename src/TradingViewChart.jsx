import React,{useEffect,useRef}from'react';
const MAP={
 XAUUSD:'OANDA:XAUUSD',EURUSD:'OANDA:EURUSD',GBPUSD:'OANDA:GBPUSD',USDJPY:'OANDA:USDJPY',BTCUSD:'BINANCE:BTCUSDT',
 NAS100:'OANDA:NAS100USD',NDX:'OANDA:NAS100USD',SPX:'OANDA:SPX500USD',SP500:'OANDA:SPX500USD',US30:'OANDA:US30USD',DJI:'OANDA:US30USD',RUT:'TVC:RUT',
 IHSG:'IDX:COMPOSITE',COMPOSITE:'IDX:COMPOSITE',LQ45:'IDX:LQ45'
};
const US_EXCHANGE={AAPL:'NASDAQ',MSFT:'NASDAQ',NVDA:'NASDAQ',AMZN:'NASDAQ',GOOGL:'NASDAQ',META:'NASDAQ',TSLA:'NASDAQ',AVGO:'NASDAQ',COST:'NASDAQ',NFLX:'NASDAQ',AMD:'NASDAQ',PLTR:'NASDAQ',JPM:'NYSE',V:'NYSE',MA:'NYSE',LLY:'NYSE',WMT:'NYSE',XOM:'NYSE',CRM:'NYSE',ORCL:'NYSE'};
const ID=new Set(['BBCA','BBRI','BMRI','BBNI','TLKM','ASII','AMMN','DSSA','BYAN','GOTO','ADRO','ANTM','INCO','MDKA','ICBP','INDF','UNVR','KLBF','PGAS','CPIN']);
function resolveSymbol(symbol){const s=String(symbol||'XAUUSD').toUpperCase();if(MAP[s])return MAP[s];if(US_EXCHANGE[s])return `${US_EXCHANGE[s]}:${s}`;if(ID.has(s))return `IDX:${s}`;return symbol}
export default function TradingViewChart({symbol='XAUUSD',interval='5'}){const ref=useRef(null);useEffect(()=>{if(!ref.current)return;ref.current.innerHTML='';const s=document.createElement('script');s.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';s.type='text/javascript';s.async=true;s.innerHTML=JSON.stringify({autosize:true,symbol:resolveSymbol(symbol),interval,timezone:'Asia/Jakarta',theme:'dark',style:'1',locale:'en',allow_symbol_change:true,calendar:true,support_host:'https://www.tradingview.com',hide_top_toolbar:false,hide_side_toolbar:false,withdateranges:true,save_image:false,details:true,hotlist:true});ref.current.appendChild(s)},[symbol,interval]);return <div className="tv-wrap"><div className="tradingview-widget-container" ref={ref} style={{height:'100%',width:'100%'}}><div className="tradingview-widget-container__widget" style={{height:'100%',width:'100%'}}/></div></div>}
