import React,{useEffect,useState}from'react';
import{createPortal}from'react-dom';
import NightChartDesk from'./NightChartDesk';

export default function NightChartInjector(){
 const[open,setOpen]=useState(false);
 useEffect(()=>{let raf=0;const apply=()=>{raf=0;const aside=document.querySelector('.prodApp aside');if(!aside||aside.querySelector('[data-night-chart]'))return;const b=document.createElement('button');b.dataset.nightChart='1';b.innerHTML='<span style="font-size:16px">⌁</span><span>NIGHT Chart</span>';b.title='Open standalone NIGHT custom chart';b.onclick=()=>setOpen(true);const order=aside.querySelector('[data-orderflow-desk]');order?aside.insertBefore(b,order):aside.appendChild(b)};const schedule=()=>{if(!raf)raf=requestAnimationFrame(apply)};apply();const mo=new MutationObserver(schedule);mo.observe(document.body,{childList:true,subtree:true});return()=>{mo.disconnect();if(raf)cancelAnimationFrame(raf)}},[]);
 return open?createPortal(<NightChartDesk onClose={()=>setOpen(false)}/>,document.body):null
}
