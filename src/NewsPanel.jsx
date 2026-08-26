import React from 'react';

function tone(v){if(v>0.18)return'good';if(v<-0.18)return'bad';return'warn'}
export default function NewsPanel({news}){const rows=news?.articles||[];return <div className="newsfeed"><div className="newshead"><b>{news?.source||'GDELT DOC 2.0'}</b><span>headline score {Number(news?.score||0).toFixed(3)}</span></div>{rows.length===0?<p>No headlines loaded.</p>:rows.slice(0,12).map((a,i)=><a className="newsrow" href={a.url} target="_blank" rel="noreferrer" key={`${a.url}-${i}`}><div><b>{a.title}</b><small>{a.domain||'source'} · {a.seen||'latest'}</small></div><span className={`pill ${tone(a.sentiment)}`}>{a.sentiment>0?'+':''}{Number(a.sentiment||0).toFixed(2)}</span></a>)}</div>}
