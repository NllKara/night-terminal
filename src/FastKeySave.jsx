import{useEffect}from'react';

export default function FastKeySave(){
 useEffect(()=>{
  const onClick=(e)=>{
   const btn=e.target?.closest?.('.prodKeys button');
   if(!btn||!String(btn.textContent||'').toUpperCase().includes('SAVE'))return;
   const panel=btn.closest('.prodKeys');if(!panel)return;
   e.preventDefault();e.stopPropagation();
   if(e.nativeEvent?.stopImmediatePropagation)e.nativeEvent.stopImmediatePropagation();
   let saved={};try{saved=JSON.parse(localStorage.getItem('night_quant_creds')||'{}')}catch{}
   panel.querySelectorAll('input').forEach(input=>{
    const p=(input.placeholder||'').toLowerCase(),v=input.value.trim();
    if(p.includes('openrouter'))saved.openrouter_key=v;
    else if(p.includes('twelve'))saved.twelve_key=v;
    else if(p.includes('fred'))saved.fred_key=v;
    else if(p.includes('gemini'))saved.gemini_key=v;
   });
   localStorage.setItem('night_quant_creds',JSON.stringify(saved));
   const keyButton=[...document.querySelectorAll('.headActions button')].find(x=>String(x.textContent||'').includes('DATA KEYS'));
   if(keyButton)setTimeout(()=>keyButton.click(),0);
   let toast=document.getElementById('night-fast-key-toast');
   if(!toast){toast=document.createElement('div');toast.id='night-fast-key-toast';document.body.appendChild(toast)}
   toast.textContent='API KEYS SAVED';toast.className='nightKeyToast show';
   clearTimeout(window.__nightKeyToastTimer);window.__nightKeyToastTimer=setTimeout(()=>toast.classList.remove('show'),1300);
  };
  document.addEventListener('click',onClick,true);return()=>document.removeEventListener('click',onClick,true)
 },[]);
 return null
}
