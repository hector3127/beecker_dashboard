/* Opportunity > linked IDs > sprint/person cost audit, loaded on demand. */
(()=>{'use strict';
 const script=document.querySelector('script[data-endpoint][src*="opportunity_details"]');
 if(!script)return;
 const cell=(tag,text,parent)=>{const e=document.createElement(tag);e.textContent=text==null?'Pendiente':String(text);parent.append(e);return e;};
 const dollars=n=>{const value=executiveMoney(n);return value==='Pendiente'?value:value.startsWith('-')?'-$'+value.slice(1):'$'+value;};
 const rate=n=>n==null?'Pendiente':'$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
 const hours=n=>n==null?'Pendiente':Number(n).toLocaleString('es-MX',{maximumFractionDigits:2});
 for(const details of document.querySelectorAll('.opportunity-people')){
  let loaded=false,busy=false;
  details.addEventListener('toggle',async()=>{
   if(!details.open||loaded||busy)return;
   busy=true;const root=details.querySelector('.opportunity-people-content');root.textContent='Consultando personas y tarifas…';
   try{
    const url=new URL(script.dataset.endpoint,location.href);url.search=location.search;url.searchParams.delete('vista');url.searchParams.set('id',details.dataset.project);url.searchParams.set('nombre',details.dataset.account);
    const response=await fetch(url,{credentials:'same-origin'}),data=await response.json();if(!response.ok||data.error)throw Error(data.error||'No se pudo consultar el detalle');
    root.replaceChildren();cell('p','Clockify: '+data.id+' · '+(data.scope_start||'')+' a '+(data.scope_end||''),root);
    const groups=(data.sprints||[]).some(g=>/^(S[0-9]|CR)/i.test(g.label))?data.sprints:[{label:'Personas',people:data.people||[]}];
    for(const group of groups){
     cell('h4',group.label,root);const scroll=cell('div','',root);scroll.style.overflow='auto';const table=cell('table','',scroll),head=cell('tr','',table);
     for(const title of ['Persona','Horas','Banda','Mes de banda','Tarifa/h','Costo','Estado'])cell('th',title,head);
     for(const person of group.people||[]){const row=cell('tr','',table);for(const value of [person.name,hours(person.hours),person.band,person.band_month,rate(person.rate),dollars(person.cost)])cell('td',value,row);const state=cell('span',person.missing?'Falta banda o tarifa':'Horas × tarifa',cell('td','',row));state.className='person-cost-state'+(person.missing?' missing':'');}
     if(!(group.people||[]).length)cell('p','Sin registros disponibles para este ID y periodo.',root);
    }
    loaded=true;
   }catch(error){root.textContent=error.message+' · Cierra y abre para reintentar.';}finally{busy=false;}
  });
 }
})();
