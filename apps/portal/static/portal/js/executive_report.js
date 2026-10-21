/* A fixed prepared cut: no per-project calls or automatic KPI replacement. */
(()=>{'use strict';
 const read=id=>{try{return JSON.parse(document.getElementById(id)?.textContent||'{}');}catch(e){return {};}};
 const seed=read('financial-cache'),ops=read('operations-cache'),money=executiveMoney;
 const loadingMetrics=new Set([
 ...(!seed.revenue?['executive-revenue','executive-collections']:[]),
 ...(!seed.costs?['executive-margin']:[]),
 ...(ops.projects==null?['executive-ops-etc','executive-ops-advance','executive-ops-facturability','executive-ops-investment']:[]),
 ...(!seed.commercial?['commercial-won','commercial-delivery','commercial-open']:[])
 ]);
 const node=id=>document.getElementById(id),set=(id,value)=>{const x=node(id);if(!x)return;if(value==='Pendiente'&&loadingMetrics.has(id)){x.classList.add('metric-loading');x.setAttribute('aria-label','Cargando dato');x.setAttribute('aria-busy','true');x.innerHTML='<span class="metric-skeleton" aria-hidden="true"></span><span class="metric-spinner" aria-hidden="true"></span><span class="metric-loading-label">Cargando dato…</span>';}else{x.textContent=value;}};
 const finishLoading=()=>{for(const id of loadingMetrics){const x=node(id);if(x?.classList.contains('metric-loading')){x.classList.remove('metric-loading');x.removeAttribute('aria-busy');x.removeAttribute('aria-label');x.textContent='No disponible';}}};
 const whole=n=>n==null?'Pendiente':Number(n).toLocaleString('en-US',{maximumFractionDigits:0});
 const pct=n=>n==null?'Pendiente':whole(n)+'%';
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const revenue=seed.revenue||{},cost=seed.costs||{};
 set('executive-revenue',money(revenue.invoiced));
 set('executive-revenue-source','Facturado: Invoiced + Collected, incluidos sus estados Factoring. Fecha disponible: DataRevenue G. Pendiente de validar el calendario de facturación con Florencia. Confirmed se conserva como revenue contratado y no se suma a facturación.');
 set('executive-collections',pct(revenue.collections_percent));
 set('executive-collections-note','Cobranza = Collected (incluido factoring) ÷ (Invoiced + Collected, incluido factoring), del periodo seleccionado según DataRevenue G. No mide cobros de facturas de otros periodos; pendiente validar fechas de cobro y factura.');
 const income=Number(revenue.invoiced),hasInvoice=revenue.invoiced!=null;
 const hasCosts=cost.cost!=null&&(cost.complete||(cost.projects||[]).some(p=>p.cost!=null)||Number(cost.deduplicated_entries)>0);
 set('executive-margin',hasCosts&&hasInvoice&&income>0?pct((income-Number(cost.cost))/income*100)+(cost.complete?'':'*'):'Pendiente');
 set('executive-margin-note',hasCosts?(cost.complete?'Costos completos · base de facturación pendiente de validar':'* Parcial con costos disponibles: '+money(cost.cost)+'.'):'Sin costos consultados para calcular el margen');
 let pendingDialog=null;
 const showPendingDialog=({title,description,columns,rows,trigger})=>{
  if(pendingDialog)pendingDialog.close();
  const dialog=document.createElement('dialog');
  dialog.className='portal-pending-dialog';
  dialog.setAttribute('aria-labelledby','pending-dialog-title');
  dialog.setAttribute('aria-describedby','pending-dialog-description');
  const headings=columns.map(c=>'<th scope="col">'+esc(c)+'</th>').join('');
  const body=rows.map(row=>'<tr>'+row.map((cell,i)=>i===0
   ?'<th scope="row">'+esc(cell)+'</th>'
   :'<td data-label="'+esc(columns[i])+'"'+(columns.length===3&&i===1?' class="pending-dialog-amount"':'')+'>'+esc(cell)+'</td>'
  ).join('')+'</tr>').join('');
  dialog.innerHTML=`<div class="pending-dialog-frame">
   <header class="pending-dialog-header"><div>
    <span class="pending-dialog-count">${whole(rows.length)} ${rows.length===1?'proyecto por revisar':'proyectos por revisar'}</span>
    <h2 id="pending-dialog-title">${esc(title)}</h2>
   </div><button type="button" class="pending-dialog-dismiss" aria-label="Cerrar pendientes" autofocus>
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>
   </button></header>
   <p id="pending-dialog-description" class="pending-dialog-description">${esc(description)}</p>
   <div class="pending-dialog-scroll" tabindex="0" role="region" aria-label="Lista de proyectos pendientes">
    <table><caption class="portal-sr-only">${esc(title)}</caption><thead><tr>${headings}</tr></thead><tbody>${body}</tbody></table>
   </div>
   <footer class="pending-dialog-footer"><span>Presiona Esc para cerrar</span><button type="button" class="portal-button portal-button-primary close-blockers">Cerrar</button></footer>
  </div>`;
  dialog.querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>dialog.close()));
  dialog.addEventListener('close',()=>{
   dialog.remove();
   if(pendingDialog===dialog){
    pendingDialog=null;
    document.documentElement.classList.remove('portal-modal-open');
    trigger.focus({preventScroll:true});
   }
  },{once:true});
  document.body.appendChild(dialog);
  pendingDialog=dialog;
  document.documentElement.classList.add('portal-modal-open');
  dialog.showModal();
 };
 const blockers=(cost.projects||[]).filter(p=>!p.complete),details=node('executive-cost-blockers');
 if(details){details.hidden=!blockers.length;details.textContent=blockers.length+' costos pendientes';details.onclick=()=>{
   showPendingDialog({title:'Pendientes de costos',description:'El margen es parcial mientras falten vínculos, fechas o tarifas. Los costos disponibles ya están incluidos en el cálculo.',columns:['Proyecto','Costo disponible','Qué falta revisar'],rows:blockers.map(p=>[p.id,money(p.cost),p.error||('Falta banda o tarifa'+(p.missing_people?.length?': '+p.missing_people.join(', '):''))]),trigger:details});
 };}
 const open=node('revenue-cost-open');if(open)open.onclick=()=>{const url=new URL(open.dataset.url,location.href);url.search=location.search;location.assign(url.toString());};
 const partial=ops.partial!==false;
 set('executive-ops-cut',ops.projects==null?'Consultando':partial?'Corte parcial':'Corte completo');
 set('executive-ops-etc',ops.etc!=null?whole(ops.etc)+' h'+(partial?'*':''):'Pendiente');
 set('executive-ops-advance',ops.advance!=null?pct(ops.advance)+(partial?'*':''):'Pendiente');
 set('executive-ops-fte',ops.fte!=null?Number(ops.fte).toLocaleString('en-US',{maximumFractionDigits:2})+' FTE equivalentes':'FTE pendiente de corte completo');
 set('executive-ops-facturability',ops.facturability==null?'Pendiente':Number(ops.facturability).toLocaleString('en-US',{maximumFractionDigits:0})+'%'+(ops.facturability_partial?'*':''));set('executive-ops-facturability-month',ops.facturability_period?(ops.facturability_partial?'Parcial · ':'')+ops.facturability_period:'');set('executive-ops-investment',ops.investment_operational==null?'Pendiente':whole(ops.investment_operational)+' h');
 const opsPending=new Map();
 for(const id of ops.missing_budget_ids||[])opsPending.set(id,['Sin presupuesto']);
 for(const id of ops.pending_ids||[])opsPending.set(id,[...(opsPending.get(id)||[]),'Consumo pendiente']);
 const opsDetails=node('executive-ops-status');
 if(opsDetails){
  opsDetails.textContent=ops.projects==null?'Preparando corte…':opsPending.size?((ops.missing_budget_ids||[]).length?whole((ops.missing_budget_ids||[]).length)+' sin presupuesto'+((ops.pending_ids||[]).length?' · '+whole((ops.pending_ids||[]).length)+' sin consumo':''):whole((ops.pending_ids||[]).length)+' sin consumo'):partial?'Corte parcial':'Corte completo';
  opsDetails.hidden=!opsPending.size;
  opsDetails.disabled=!opsPending.size;
  opsDetails.onclick=()=>{
   if(!opsPending.size)return;
   showPendingDialog({title:'Pendientes de Operaciones',description:'Estos proyectos necesitan presupuesto o consumo para completar el corte operativo.',columns:['Proyecto','Qué falta revisar'],rows:[...opsPending].map(([id,reasons])=>[id,reasons.join(' · ')]),trigger:opsDetails});
  };
 }
 set('executive-ops-note','Las horas de inversión operativa corresponden a los registros del periodo seleccionado. Los indicadores se muestran como parciales cuando falta cobertura.');
 const commercial=seed.commercial||{};set('commercial-won',money(commercial.won));set('commercial-won-note',commercial.won_count==null?'Pendiente de corte':whole(commercial.won_count)+' ventas ganadas · booking');
 set('commercial-delivery',money(commercial.delivery));set('commercial-delivery-note',commercial.delivery_note||'Pendiente de corte');
 const deliveryNode=node('commercial-delivery');if(deliveryNode)deliveryNode.title=commercial.delivery_note||'Revenue futuro Confirmed por fecha de Finanzas';
 set('commercial-open',money(commercial.open));set('commercial-open-note',commercial.open_note||'Pendiente de corte');
 const openNode=node('commercial-open');if(openNode)openNode.title=commercial.open_note||'Oportunidades abiertas del periodo';
 set('commercial-data-state',commercial.open_rule&&commercial.delivery_rule?'Corte preparado':'Validaciones pendientes');
 const savedMonthly=seed.profitability;
 const monthly=savedMonthly?{...savedMonthly,months:(savedMonthly.months||[]).map(row=>({...row,margin:row.cost!=null&&Number(row.revenue)>0?(Number(row.revenue)-Number(row.cost))/Number(row.revenue)*100:null}))}:null,chart=node('monthly-profit-chart');
 if(monthly&&chart){mountExecutiveMonthlyChart(chart,monthly);set('monthly-profit-state',monthly.complete?'Corte preparado':'Margen parcial · costos disponibles');}else if(chart)chart.textContent='El corte del periodo se está preparando. Las cifras no se actualizarán automáticamente.';
 set('monthly-profit-note','Facturación mensual = Invoiced + Collected (incluido factoring), por mes de DataRevenue G; no usa el monto total del proyecto. Costos por fecha de cada registro de Clockify. Fechas y conceptos de facturación pendientes de validar con Florencia. La línea muestra el margen con los costos disponibles; * indica un margen parcial que puede cambiar al completar costos.');
 set('ranking-coverage','Ordenado por los dos indicadores monetarios normalizados; el porcentaje de margen no determina el orden. '+whole(seed.accounts?.pending_accounts||0)+' cuentas incluidas con costos parciales (*).');
 for(const [kind,rows] of [['healthy',seed.accounts?.healthy],['unhealthy',seed.accounts?.unhealthy]]){
  set(kind+'-account-count',rows?rows.length+' cuentas':'Pendiente');
  const target=node(kind+'-financial-accounts');if(!target)continue;
  target.innerHTML=(rows||[]).map((a,i)=>'<tr><td>'+(i+1)+'</td><td><a class="ranking-account" href="'+esc(a.url)+'">'+esc(a.name)+'</a><small>'+whole(a.projects)+' proyectos'+(a.pending?' · Parcial*':'')+'</small></td><td>'+money(a.revenue)+'</td><td class="ranking-margin"><strong>'+money(a.gross_profit)+(a.pending?'*':'')+'</strong></td><td class="ranking-margin"><b>'+(a.margin==null?'No aplica':pct(a.margin)+(a.pending?'*':''))+'</b></td></tr>').join('')||'<tr><td colspan="5">'+(seed.accounts?'No hay cuentas elegibles para este grupo. '+whole(seed.accounts.pending_accounts||0)+' con costos parciales.':'Corte del ranking pendiente de preparar.')+'</td></tr>';
 }
 const control=node('executive-prepare'),status=node('executive-cut-status');
 if(!control||!status)return;
 const coverage=cost.projects?Math.max(0,cost.projects.length-Number(cost.pending||0))+' de '+cost.projects.length+' proyectos con costos consultados':'';
 if(seed.loaded_at)status.textContent='Última consulta: '+new Date(seed.loaded_at).toLocaleString('es-MX')+(coverage?' · '+coverage:'');else status.textContent='Consultando datos del periodo…';
 control.textContent='Actualizar datos';
 let ready=false,timer=null,applyWhenReady=!seed.loaded_at;const missingBlocks=!seed.loaded_at||ops.projects==null||!seed.commercial;
 const url=new URL(control.dataset.endpoint,location.href);url.search=location.search;
 const check=async()=>{try{const r=await fetch(url,{credentials:'same-origin'});if(!r.ok)throw Error();const data=await r.json();if((!seed.loaded_at&&data.has_financial_cut)||(!seed.commercial&&data.has_commercial_cut)||(ops.projects==null&&data.has_operations_cut)){clearInterval(timer);location.reload();return;}if(data.state==='ready'){clearInterval(timer);finishLoading();if(data.has_financial_cut===false){applyWhenReady=false;control.disabled=false;status.textContent='No se pudo completar la consulta financiera. Pulsa Actualizar datos para reintentar; no se mostrarán cifras inventadas.';return;}if(applyWhenReady){applyWhenReady=false;status.textContent='Datos consultados. Mostrando el resultado…';location.reload();return;}ready=true;control.disabled=false;control.textContent='Ver corte preparado';status.textContent=data.partial?'Corte preparado con pendientes identificados. Pulsa para verlo.':'Nuevo corte preparado. Pulsa para verlo.';}else if(data.state==='failed'){clearInterval(timer);finishLoading();control.disabled=false;status.textContent='No se pudo completar. Se conserva el corte mostrado.';}else if(data.state==='running'||data.state==='queued'){status.textContent='Preparando en segundo plano. Se conserva el corte mostrado.';}}catch(e){clearInterval(timer);finishLoading();control.disabled=false;status.textContent='Sin conexión para actualizar. Se conserva el corte mostrado.';}};
 control.onclick=async()=>{if(ready){location.reload();return;}applyWhenReady=true;control.disabled=true;status.textContent='Consultando fuentes en segundo plano…';try{const csrf=document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';const r=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'X-CSRFToken':csrf}});if(!r.ok)throw Error();await check();if(!ready&&applyWhenReady)timer=setInterval(check,5000);}catch(e){control.disabled=false;status.textContent='No se pudo iniciar la actualización.';}};
 if(missingBlocks){timer=setInterval(check,5000);check();}
})();
