import React from 'react';
import jsPDF from 'jspdf';

function line(doc,label,value,y){doc.setFont('helvetica','bold');doc.text(label,18,y);doc.setFont('helvetica','normal');doc.text(String(value??'—'),68,y);return y+7}

export default function ReportButton({symbol,timeframe,data,mtf,news}){
 function generate(){
  const d=data||{};const math=d.math||{};const vp=d.volume_profile||{};const comp=d.components||{};
  const doc=new jsPDF({unit:'mm',format:'a4'});let y=18;
  doc.setFont('helvetica','bold');doc.setFontSize(20);doc.text('NIGHT QUANT INSTITUTIONAL REPORT',18,y);y+=8;
  doc.setFontSize(9);doc.setFont('helvetica','normal');doc.text(`${symbol} · ${timeframe} · ${new Date().toLocaleString()}`,18,y);y+=10;
  doc.setDrawColor(60);doc.line(18,y,192,y);y+=8;
  doc.setFontSize(12);doc.setFont('helvetica','bold');doc.text('Executive Quant Verdict',18,y);y+=8;doc.setFontSize(10);
  y=line(doc,'Bias',d.bias,y);y=line(doc,'Action',d.action,y);y=line(doc,'P(up)',`${d.probability_up??'—'}%`,y);y=line(doc,'P(down)',`${d.probability_down??'—'}%`,y);y=line(doc,'Edge',d.edge,y);y=line(doc,'Confidence',`${d.confidence??'—'}%`,y);y=line(doc,'Readiness',`${d.trade_readiness??'—'}%`,y);y=line(doc,'EV Long',`${d.ev_long_r??'—'}R`,y);y=line(doc,'EV Short',`${d.ev_short_r??'—'}R`,y);y+=4;
  doc.setFont('helvetica','bold');doc.text('Market / Volume',18,y);y+=7;doc.setFont('helvetica','normal');y=line(doc,'Last price',d.last_price,y);y=line(doc,'Volume source',d.source,y);y=line(doc,'Volume type',d.volume_type,y);y=line(doc,'VAH',vp.vah,y);y=line(doc,'POC',vp.poc,y);y=line(doc,'VAL',vp.val,y);y=line(doc,'Buyer aggression',`${d.buyer_aggression??'—'}%`,y);y=line(doc,'Seller aggression',`${d.seller_aggression??'—'}%`,y);
  if(y>255){doc.addPage();y=18}y+=4;doc.setFont('helvetica','bold');doc.text('Quant Statistics',18,y);y+=7;doc.setFont('helvetica','normal');Object.entries(math).slice(0,12).forEach(([k,v])=>{y=line(doc,k.replaceAll('_',' '),v,y);if(y>275){doc.addPage();y=18}});
  if(y>250){doc.addPage();y=18}y+=4;doc.setFont('helvetica','bold');doc.text('Weighted Factors',18,y);y+=7;doc.setFont('helvetica','normal');Object.entries(comp).forEach(([k,v])=>{y=line(doc,k,v,y)});
  if(mtf?.valid){if(y>235){doc.addPage();y=18}y+=4;doc.setFont('helvetica','bold');doc.text('Multi-Timeframe Consensus',18,y);y+=7;doc.setFont('helvetica','normal');y=line(doc,'HTF P(up)',`${mtf.probability_up}%`,y);y=line(doc,'Agreement',`${mtf.agreement}%`,y);Object.entries(mtf.timeframes||{}).forEach(([tf,r])=>{y=line(doc,tf,`${r.action||'—'} · P(up) ${r.probability_up??'—'}%`,y)});}
  if(y>220){doc.addPage();y=18}y+=4;doc.setFont('helvetica','bold');doc.text('Macro / Positioning / News',18,y);y+=7;doc.setFont('helvetica','normal');y=line(doc,'Macro source',d.macro_source||'—',y);y=line(doc,'COT score',d.cot?.score??'—',y);y=line(doc,'News score',d.news?.score??'—',y);(news?.articles||d.news?.articles||[]).slice(0,6).forEach((a,i)=>{const text=doc.splitTextToSize(`${i+1}. ${a.title}`,170);doc.text(text,18,y);y+=text.length*5+2;if(y>275){doc.addPage();y=18}});
  if(y>245){doc.addPage();y=18}y+=4;doc.setFont('helvetica','bold');doc.text('Model Thesis',18,y);y+=7;doc.setFont('helvetica','normal');let t=doc.splitTextToSize(d.scenario||d.reason||'No thesis.',170);doc.text(t,18,y);y+=t.length*5+5;doc.setFont('helvetica','bold');doc.text('Invalidation',18,y);y+=6;doc.setFont('helvetica','normal');t=doc.splitTextToSize(d.invalidation||'—',170);doc.text(t,18,y);y+=t.length*5+5;
  doc.setFontSize(8);doc.setTextColor(110);doc.text('Decision-support research output. Probabilities are model estimates, not certainty or financial advice.',18,288);
  doc.save(`NIGHT_${symbol}_${timeframe}_${new Date().toISOString().slice(0,10)}.pdf`);
 }
 return <button className="ghost" onClick={generate}>EXPORT INSTITUTIONAL PDF</button>
}
