import React from 'react';
import {Brain, Gauge, Flame, Globe2, Newspaper, CalendarClock, ShieldCheck, FileText, FlaskConical, MessageSquare, Crosshair} from 'lucide-react';

export const ENGINES=[
 {id:'master',label:'Master Quant',desc:'Institutional multi-factor decision engine',icon:Brain},
 {id:'execution',label:'Execution',desc:'Entry, invalidation, targets and timing',icon:Crosshair},
 {id:'volume',label:'Volume & Flow',desc:'VP, pressure, aggression and acceptance',icon:Flame},
 {id:'statistics',label:'Statistics',desc:'Returns, OLS, z-scores, volatility and regime',icon:Gauge},
 {id:'intermarket',label:'Intermarket',desc:'Cross-asset confirmation and divergence',icon:Globe2},
 {id:'news',label:'News Intelligence',desc:'Live headlines, relevance and event risk',icon:Newspaper},
 {id:'events',label:'Event Engine',desc:'Calendar and event-risk state',icon:CalendarClock},
 {id:'risk',label:'Risk Engine',desc:'EV, risk state and execution constraints',icon:ShieldCheck},
 {id:'backtest',label:'Model Validation',desc:'Calibration and walk-forward research',icon:FlaskConical},
 {id:'chat',label:'Quant Chat',desc:'Interrogate the current market state',icon:MessageSquare},
 {id:'report',label:'Report Engine',desc:'On-demand institutional PDF report',icon:FileText},
];

export default function EngineSelector({value,onChange}){
 return <div className="engineSelect"><span>ENGINE</span><select value={value} onChange={e=>onChange(e.target.value)}>{ENGINES.map(e=><option key={e.id} value={e.id}>{e.label}</option>)}</select><small>{ENGINES.find(e=>e.id===value)?.desc}</small></div>
}
