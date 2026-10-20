/* A fixed prepared cut: no per-project calls or automatic KPI replacement. */
(()=>{'use strict';
 const read=id=>{try{return JSON.parse(document.getElementById(id)?.textContent||'{}');}catch(e){return {};}};
 const seed=read('financial-cache'),ops=read('operations-cache'),money=executiveMoney;
 const node=id=>document.getElementById(id),set=(id,value)=>{const x=node(id);if(x)x.textContent=value;};
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
 set('executive-margin-note',hasCosts?(cost.complete?'Costos completos · base de facturación pendiente de validar':'* Parcial con costos disponibles: '+money(cost.cost)+' · '+whole((cost.projects||[]).filter(p=>!p.complete).length||cost.pending||0)+' proyectos pendientes. Puede cambiar al completar costos.'):'Sin costos consultados para calcular el margen');
 const blockers=(cost.projects||[]).filter(p=>!p.complete),details=node('executive-cost-blockers');
 if(details){details.hidden=!blockers.length;details.textContent='Ver '+blockers.length+' pendientes de costos';details.onclick=()=>{
   const dialog=document.createElement('dialog');dialog.style.cssText='width:min(1000px,92vw);max-height:85vh;border:1px solid #e4d9ff;border-radius:16px;padding:22px;color:#241651';
   dialog.innerHTML='<h2>Consultas pendientes de costos</h2><p>El margen no se publica como completo mientras falten vínculos, fechas o tarifas. Los registros ya consultados sí están incluidos en los costos disponibles.</p><div style="overflow:auto"><table style="width:100%;font-size:13px"><thead><tr><th>Proyecto</th><th>Costo disponible</th><th>Motivo</th></tr></thead><tbody>'+blockers.map(p=>'<tr><td>'+esc(p.id)+'</td><td>'+money(p.cost)+'</td><td>'+esc(p.error||('Falta banda o tarifa'+(p.missing_people?.length?': '+p.missing_people.join(', '):'')))+'</td></tr>').join('')+'</tbody></table></div><button type="button" class="close-blockers">Cerrar</button>';
   dialog.querySelector('.close-blockers').onclick=()=>dialog.close();dialog.addEventListener('close',()=>dialog.remove());document.body.appendChild(dialog);dialog.showModal();
 };}
 const open=node('revenue-cost-open');if(open)open.onclick=()=>{const url=new URL(open.dataset.url,location.href);url.search=location.search;location.assign(url.toString());};
 const partial=ops.partial!==false;
 set('executive-ops-cut',ops.projects==null?'Consultando':partial?'Corte parcial':'Corte completo');
 set('executive-ops-etc',ops.etc!=null?whole(ops.etc)+' h'+(partial?'*':''):'Pendiente');
 set('executive-ops-advance',ops.advance!=null?pct(ops.advance)+(partial?'*':''):'Pendiente');
 set('executive-ops-fte',ops.fte!=null?Number(ops.fte).toLocaleString('en-US',{maximumFractionDigits:2})+' FTE equivalentes':'FTE pendiente de corte completo');
 set('executive-ops-facturability',ops.facturability==null?'Pendiente':Number(ops.facturability).toLocaleString('en-US',{maximumFractionDigits:2})+'%'+(ops.facturability_partial?'*':''));set('executive-ops-facturability-month',ops.facturability_period?(ops.facturability_partial?'Parcial · ':'')+ops.facturability_period:'');set('executive-ops-investment',ops.investment_operational==null?'Pendiente':whole(ops.investment_operational)+' h');
 const opsPending=new Map();
 for(const id of ops.missing_budget_ids||[])opsPending.set(id,['Sin presupuesto']);
 for(const id of ops.pending_ids||[])opsPending.set(id,[...(opsPending.get(id)||[]),'Consumo pendiente']);
 const opsDetails=node('executive-ops-status');
 if(opsDetails){
  opsDetails.textContent=ops.projects==null?'Preparando corte…':opsPending.size?((ops.missing_budget_ids||[]).length?'Ver '+whole((ops.missing_budget_ids||[]).length)+' sin presupuesto'+((ops.pending_ids||[]).length?' · '+whole((ops.pending_ids||[]).length)+' sin consumo':''):'Ver '+whole((ops.pending_ids||[]).length)+' sin consumo'):partial?'Corte parcial':'Corte completo';
  opsDetails.disabled=!opsPending.size;
  opsDetails.onclick=()=>{
   if(!opsPending.size)return;
   const dialog=document.createElement('dialog');dialog.style.cssText='width:min(760px,92vw);max-height:85vh;border:1px solid #e4d9ff;border-radius:16px;padding:22px;color:#241651';
   dialog.innerHTML='<h2>Pendientes de Operaciones</h2><div style="overflow:auto"><table style="width:100%;font-size:13px"><thead><tr><th>Proyecto</th><th>Motivo</th></tr></thead><tbody>'+[...opsPending].map(([id,reasons])=>'<tr><td>'+esc(id)+'</td><td>'+esc(reasons.join(' · '))+'</td></tr>').join('')+'</tbody></table></div><button type="button" class="close-blockers">Cerrar</button>';
   dialog.querySelector('.close-blockers').onclick=()=>dialog.close();dialog.addEventListener('close',()=>dialog.remove());document.body.appendChild(dialog);dialog.showModal();
  };
 }
 set('executive-ops-note','ETC = presupuesto − consumo. FTE equivalente = ETC ÷ meses del rango ÷ 360 (base solicitada por Dirección). Avance = consumo ÷ presupuesto. Facturabilidad de proyectos = horas facturables ÷ todas las horas de sus registros. Inversión operativa = horas con etiqueta INV_OPERATIVA. No equivale a la facturabilidad global de GSE.');
 const commercial=seed.commercial||{};set('commercial-won',money(commercial.won));set('commercial-won-note',commercial.won_count==null?'Pendiente de corte':whole(commercial.won_count)+' ventas ganadas · booking');
 set('commercial-delivery','Pendiente');set('commercial-delivery-note','Poly: saldo por ejecutar pendiente de validar');
 set('commercial-open','Pendiente');set('commercial-open-note','Luis Enrique: categoría previa al cierre pendiente de definir');set('commercial-data-state','Validaciones pendientes');
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
 let ready=false,timer=null,applyWhenReady=!seed.loaded_at;
 const url=new URL(control.dataset.endpoint,location.href);url.search=location.search;
 const check=async()=>{try{const r=await fetch(url,{credentials:'same-origin'});if(!r.ok)throw Error();const data=await r.json();if(data.state==='ready'){clearInterval(timer);if(data.has_financial_cut===false){applyWhenReady=false;control.disabled=false;status.textContent='No se pudo completar la consulta financiera. Pulsa Actualizar datos para reintentar; no se mostrarán cifras inventadas.';return;}if(applyWhenReady){applyWhenReady=false;status.textContent='Datos consultados. Mostrando el resultado…';location.reload();return;}ready=true;control.disabled=false;control.textContent='Ver corte preparado';status.textContent=data.partial?'Corte preparado con pendientes identificados. Pulsa para verlo.':'Nuevo corte preparado. Pulsa para verlo.';}else if(data.state==='failed'){clearInterval(timer);control.disabled=false;status.textContent='No se pudo completar. Se conserva el corte mostrado.';}else if(data.state==='running'||data.state==='queued'){status.textContent='Preparando en segundo plano. Se conserva el corte mostrado.';}}catch(e){clearInterval(timer);control.disabled=false;status.textContent='Sin conexión para actualizar. Se conserva el corte mostrado.';}};
 control.onclick=async()=>{if(ready){location.reload();return;}applyWhenReady=true;control.disabled=true;status.textContent='Consultando fuentes en segundo plano…';try{const csrf=document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';const r=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'X-CSRFToken':csrf}});if(!r.ok)throw Error();await check();if(!ready&&applyWhenReady)timer=setInterval(check,5000);}catch(e){control.disabled=false;status.textContent='No se pudo iniciar la actualización.';}};
 if(!seed.loaded_at){timer=setInterval(check,5000);check();}
})();
