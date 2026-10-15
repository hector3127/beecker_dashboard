
(function(){
  'use strict';
  const st={mes:'',base:null,meta:new Map(),request:0,q:'',tecnologia:'',concepto:'',jornada:8,view:'matrix',page:1,size:30,busy:false,progreso:''};
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm=v=>String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const fmt=n=>Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:2});
  const date=d=>d?d.slice(8,10)+'/'+d.slice(5,7)+'/'+d.slice(0,4):'—';
  const icon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V11m5 9V6m5 14V9m5 11V3" stroke-linecap="round"/></svg>';
  const key=f=>f.idProyecto+'|'+f.iteration;
  function days(month){const [y,m]=month.split('-').map(Number),out=[];for(let d=new Date(Date.UTC(y,m-1,1));d.getUTCMonth()===m-1;d.setUTCDate(d.getUTCDate()+1)){if(d.getUTCDay()!==0&&d.getUTCDay()!==6)out.push(d.toISOString().slice(0,10));}return out;}
  function workdays(a,b){if(!a||!b||a>b)return 0;let n=0;for(let d=new Date(a+'T12:00:00Z'),end=new Date(b+'T12:00:00Z');d<=end;d.setUTCDate(d.getUTCDate()+1)){if(d.getUTCDay()!==0&&d.getUTCDay()!==6)n++;}return n;}
  function computed(){
    const d=days(st.mes),all=[],people=new Map();
    /* Quien esta "Sin Asignación" no cuenta como recurso del mes. */
    (st.base&&st.base.filas||[]).filter(f=>norm(f.concepto)!=='sin asignacion').forEach(f=>{
      const last=new Date(Date.UTC(Number(st.mes.slice(0,4)),Number(st.mes.slice(5)),0)).toISOString().slice(0,10);
      const meta=f.idProyecto?st.meta.get(key(f)):{ok:true,inicio:st.mes+'-01',fin:last};
      if(f.idProyecto&&meta&&(meta.fueraMes||(meta.inicio&&meta.fin&&(meta.fin<st.mes+'-01'||meta.inicio>last))))return;
      const per=null;
      const status=!meta?'Consultando Clockify':!meta.ok?meta.error:!f.regla?'Concepto sin regla':null;
      const values=d.map(day=>!f.idProyecto?0:meta&&meta.ok?Number((meta.daily[norm(f.recurso)]||{})[day]||0):null);
      const total=values.reduce((n,v)=>n+(v||0),0);
      const x=Object.assign({},f,{inicio:meta&&meta.inicio,fin:meta&&meta.fin,values,total,status,per});all.push(x);
      const k=norm(f.recurso).trim();if(!people.has(k))people.set(k,{nombre:f.recurso,tecnologia:f.tecnologia,banda:f.banda,values:d.map(()=>0),total:0,fact:0,carg:0,unknown:false});
      const p=people.get(k);if(status)p.unknown=true;
      if(f.regla&&f.regla.afecta){values.forEach((v,i)=>p.values[i]+=v||0);p.total+=total;}
      if(f.regla&&f.regla.facturable==='Facturable')p.fact+=total;
      if(f.regla&&f.regla.cargabilidad==='Cargable')p.carg+=total;
    });
    const available=Array.from(people.values()).reduce((n,p)=>n+p.values.reduce((s,v)=>s+Math.max(0,st.jornada-v),0),0);
    return {days:d,all,people:Array.from(people.values()),available};
  }
  window.ciCancelar=function(){st.request++;st.busy=false;};
  window.ciAbrir=function(){
    if(document.getElementById('ci-panel'))return;
    const panel=document.createElement('section');panel.id='ci-panel';panel.className='ci-overlay';panel.setAttribute('role','region');panel.setAttribute('aria-label','Capacidad instalada');
    const svg=(path)=>'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">'+path+'</svg>';
    const calendar=svg('<rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 3v4m8-4v4M4 10h16"/>');
    const clock=svg('<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>');
    const search=svg('<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>');
    const layers=svg('<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>');
    const field=(label,ico,control)=>'<label>'+label+'<span class="ci-field">'+ico+control+'</span></label>';
    panel.innerHTML='<div class="ci-wrap"><div class="ci-head"><div class="ci-title"><span class="ci-icon">'+icon+'</span><div><h1>Capacidad instalada</h1><div class="ci-muted">Horas reales del equipo · Recursos + MPB/Azure + Clockify + Bandas/rol</div></div></div></div><div class="ci-filter-card"><div class="ci-toolbar">'+
    field('Mes',calendar,'<input type="month" id="ci-month" onchange="ciMes(this.value)">')+
    field('Jornada diaria (h)',clock,'<input id="ci-jornada" type="number" min="1" max="24" step="0.5" value="'+st.jornada+'" onchange="ciJornada(this.value)">')+
    field('Buscar recurso, proyecto o manager…',search,'<input id="ci-search" placeholder="Buscar recurso, proyecto o manager…" oninput="ciFiltro(\'q\',this.value)">')+
    field('Tecnologías',layers,'<select id="ci-role" onchange="ciFiltro(\'tecnologia\',this.value)"><option value="">Todas las tecnologías</option></select>')+
    field('Conceptos',layers,'<select id="ci-concept" onchange="ciFiltro(\'concepto\',this.value)"><option value="">Todos los conceptos</option></select>')+
    '<button class="ci-btn" onclick="ciRefrescar()">↻ Actualizar datos</button><button class="ci-btn primary" onclick="ciExportar()">↓ Exportar CSV</button></div><div class="ci-sourcebar"><span class="ci-sourcechip" id="ci-monthchip">'+calendar+'Mes</span><span class="ci-sourcechip">'+layers+'Recursos + Bandas/rol</span><span>+</span><span class="ci-sourcechip">'+layers+'MPB / Azure DevOps</span><span>+</span><span class="ci-sourcechip">'+clock+'Clockify</span><span class="ci-sourcechip" id="ci-bandchip">'+layers+'Banda</span><div id="ci-status">Leyendo asignaciones…</div></div></div><div id="ci-content"></div></div>';
    document.getElementById('capacity-detail-root').appendChild(panel);const requested=new URLSearchParams(window.location.search).get('mes');const now=new Date();st.mes=/^\d{4}-(0[1-9]|1[0-2])$/.test(requested||'')?requested:now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0');document.getElementById('ci-month').value=st.mes;load(false);
  };
  window.ciMes=function(m){if(!/^\d{4}-\d{2}$/.test(m))return;st.mes=m;st.page=1;load(false);};
  window.ciJornada=function(v){const n=Number(v);if(n>=1&&n<=24){st.jornada=n;paint();}};
  window.ciFiltro=function(k,v){st[k]=v;st.page=1;paint();};
  window.ciVista=function(v){st.view=v;st.page=1;paint();};
  window.ciPagina=function(delta){st.page=Math.max(1,st.page+delta);paint();};
  window.ciRefrescar=function(){load(true);};
  function message(s,error){const e=document.getElementById('ci-status');if(e){e.textContent=s;e.classList.toggle('ci-error',!!error);}}
  function fillFilters(r){
    document.getElementById('ci-monthchip').textContent='▣ Mes '+r.mes;document.getElementById('ci-bandchip').textContent='◇ Banda: '+(r.bandaColumna||'NA');document.getElementById('ci-month').value=r.mes;
    ['tecnologia','concepto'].forEach(k=>{const el=document.getElementById(k==='tecnologia'?'ci-role':'ci-concept');el.innerHTML='<option value="">'+(k==='tecnologia'?'Todas las tecnologías':'Todos los conceptos')+'</option>'+Array.from(new Set(r.filas.map(f=>f[k]).filter(Boolean))).sort().map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');el.value=st[k];});
  }
  function load(force){
    const token=++st.request;st.busy=true;message('Leyendo Recursos y Bandas/rol…');
    google.script.run.withSuccessHandler(r=>{
      if(token!==st.request)return;st.busy=false;if(!r||!r.ok){message(r&&r.error||'No se pudieron leer las hojas.',true);return;}
      st.base=r;st.mes=r.mes;fillFilters(r);
      paint();loadDates(force,token);
    }).withFailureHandler(e=>{if(token!==st.request)return;st.busy=false;message(e.message||String(e),true);}).capacidadInstaladaBase(st.mes);
  }
  function loadDates(force,token){
    const queue=Array.from(new Map(st.base.filas.filter(f=>f.idProyecto).map(f=>[key(f),f])).values()).filter(f=>force||!st.meta.has(key(f))||st.meta.get(key(f)).mes!==st.mes||!st.meta.get(key(f)).ok);
    const queryMonth=st.mes;let next=0,completed=0,active=0;
    function pump(){
      if(token!==st.request)return;
      message(queue.length?'MPB/Azure + Clockify: '+completed+' / '+queue.length+' proyectos consultados':'Datos disponibles · '+st.base.filas.length+' asignaciones');
      while(active<2&&next<queue.length){const f=queue[next++];active++;google.script.run.withSuccessHandler(r=>finish(f,r)).withFailureHandler(e=>finish(f,{ok:false,error:e.message||String(e)})).capacidadInstaladaDatosProyecto(f.idProyecto,f.iteration,st.mes,force);}
      if(!active&&completed===queue.length){st.busy=false;paint();message('Mes '+st.mes+' · '+st.base.fuentes.join(' + ')+' + Clockify'+' · Banda: '+(st.base.bandaColumna||'NA'));}
    }
    function finish(f,r){st.meta.set(key(f),Object.assign({mes:queryMonth},r||{ok:false,error:'Clockify no devolvió datos'}));if(token!==st.request)return;active--;completed++;paint();pump();}
    st.busy=queue.length>0;pump();
  }
  function selected(rows){return rows.filter(x=>(!st.tecnologia||x.tecnologia===st.tecnologia)&&(!st.concepto||x.concepto===st.concepto)&&(!st.q||norm([x.recurso,x.idProyecto,x.proyecto,x.manager,x.rol,x.banda].join(' ')).includes(norm(st.q))));}
  function paint(){
    const box=document.getElementById('ci-content');if(!box||!st.base)return;
    const data=computed(),rows=selected(data.all),capacity=data.people.length*data.days.length*st.jornada;
    const pending=data.all.filter(x=>x.status).length,over=data.people.filter(p=>p.values.some(v=>v>st.jornada+0.001)).length;
    const fact=data.all.filter(x=>x.regla&&x.regla.facturable==='Facturable').reduce((s,x)=>s+x.total,0),carg=data.all.filter(x=>x.regla&&x.regla.cargabilidad==='Cargable').reduce((s,x)=>s+x.total,0);
    const stats=[['Recursos',data.people.length,'Personas únicas del mes'],['Capacidad base',fmt(capacity)+' h',data.days.length+' días × '+st.jornada+' h'],['Horas facturables',fmt(fact)+' h','Cargables: '+fmt(carg)+' h'],['Capacidad disponible',pending?'Pendiente':fmt(data.available)+' h',pending?'Hay asignaciones pendientes':'Suma diaria por persona'],['Sobre jornada',over,'Más de '+st.jornada+' h en algún día']];
    box.innerHTML='<div class="ci-kpis">'+stats.map(x=>'<div class="ci-card ci-stat"><span class="ci-icon">'+icon+'</span><div><small>'+esc(x[0])+'</small><strong>'+esc(x[1])+'</strong><small>'+esc(x[2])+'</small></div></div>').join('')+'</div>'+
      (st.base.bandasAviso?'<div class="ci-alert">'+esc(st.base.bandasAviso)+'</div>':'')+
      (pending?'<div class="ci-alert">'+pending+' asignación(es) requieren completar fechas, horas o concepto. Las celdas pendientes se muestran con «—». Los totales de horas son parciales hasta resolverlas.</div>':'')+
      '<div class="ci-card"><div class="ci-section-head"><h3>Asignación del mes · '+esc(st.mes)+'</h3><div class="ci-pills"><button class="ci-btn '+(st.view==='matrix'?'primary':'')+'" onclick="ciVista(\'matrix\')">Matriz de asignaciones</button><button class="ci-btn '+(st.view==='people'?'primary':'')+'" onclick="ciVista(\'people\')">Capacidad por recurso</button></div></div>'+(st.view==='matrix'?matrix(rows,data):resources(data))+'</div>'+
      '<div class="ci-info"><b>Cálculo:</b> horas reales registradas en Clockify por persona, proyecto y día del mes seleccionado. No se reparten horas estimadas. La capacidad disponible suma por persona y día: máximo de 0 y (jornada − horas que afectan capacidad). Los excedentes se resaltan en rojo. Las fechas se incluyen completas y los nombres de banda/tecnología se cruzan por nombre normalizado. Fines de semana excluidos; no se descuentan festivos sin calendario. <b>Los indicadores superiores corresponden al mes completo; los filtros actúan sobre la tabla.</b></div>';
  }
  function matrix(rows,data){
    const pages=Math.max(1,Math.ceil(rows.length/st.size));st.page=Math.min(st.page,pages);const shown=rows.slice((st.page-1)*st.size,st.page*st.size);
    const headings=['Recurso','Banda','Conceptos','Facturable','Cargabilidad','Capacidad Disponible','Tecnología','Delivery Manager','ID Proyecto','Proyecto','Inicio','Fin','Total mes'];
    const pill=(v,c)=>'<span class="ci-pill '+c+'">'+esc(v||'NA')+'</span>';
    return '<div class="ci-matrix"><table class="ci-table"><thead><tr>'+headings.map(h=>'<th>'+h+'</th>').join('')+data.days.map(d=>'<th class="ci-day-head"><span>'+date(d)+'</span></th>').join('')+'</tr></thead><tbody>'+shown.map(f=>'<tr><td><b>'+esc(f.recurso)+'</b>'+(f.status?'<small class="ci-muted">'+esc(f.status)+'</small>':'')+'</td><td>'+pill(f.banda,'')+'</td><td>'+pill(f.concepto,'')+'</td><td>'+pill(f.regla&&f.regla.facturable,f.regla&&f.regla.facturable==='Facturable'?'green':'grey')+'</td><td>'+pill(f.regla&&f.regla.cargabilidad,f.regla&&f.regla.cargabilidad==='Cargable'?'blue':'grey')+'</td><td>'+pill(f.regla&&f.regla.capacidad,'')+'</td><td>'+esc(f.tecnologia||'—')+'</td><td>'+esc(f.manager||'—')+'</td><td>'+esc(f.idProyecto||'—')+'</td><td>'+esc(f.proyecto||'—')+'</td><td>'+date(f.inicio)+'</td><td>'+date(f.fin)+'</td><td><b>'+fmt(f.total)+'</b></td>'+f.values.map((v,i)=>{const p=data.people.find(p=>norm(p.nombre).trim()===norm(f.recurso).trim());return '<td class="ci-day '+(v==null?'pending':!v?'off':p&&p.values[i]>st.jornada+0.001?'over':'')+'">'+(v==null?'—':v?fmt(v):'')+'</td>';}).join('')+'</tr>').join('')+'</tbody></table></div><div class="ci-foot"><small class="ci-muted">'+rows.length+' asignaciones · Página '+st.page+' de '+pages+' · '+st.size+' filas por página</small><div><button class="ci-btn" onclick="ciPagina(-1)" '+(st.page===1?'disabled':'')+'>← Anterior</button> <button class="ci-btn" onclick="ciPagina(1)" '+(st.page===pages?'disabled':'')+'>Siguiente →</button></div></div>';
  }
  function resources(data){return '<div class="ci-resource-grid">'+data.people.filter(p=>(!st.tecnologia||p.tecnologia===st.tecnologia)&&(!st.q||norm(p.nombre+' '+p.tecnologia).includes(norm(st.q)))).map(p=>{const base=data.days.length*st.jornada,used=p.total,free=p.values.reduce((n,v)=>n+Math.max(0,st.jornada-v),0),over=p.values.some(v=>v>st.jornada+0.001);return '<div class="ci-resource"><b>'+esc(p.nombre)+'</b><div class="ci-muted">'+esc(p.tecnologia||'NA')+' · '+esc(p.banda)+'</div><div class="ci-pills" style="margin-top:9px"><span class="ci-pill '+(over?'red':'green')+'">'+(p.unknown?'Pendiente de datos':over?'Sobre jornada':'Dentro de capacidad')+'</span></div><div class="ci-muted" style="margin-top:9px">Registradas: '+fmt(used)+' h · Base: '+fmt(base)+' h<br>Disponibles: '+(p.unknown?'—':fmt(free)+' h')+'</div><div class="ci-bar"><i style="width:'+Math.min(100,base?used/base*100:0)+'%;background:'+(over?'#f13564':'#6734df')+'"></i></div></div>';}).join('')+'</div>';}
  window.ciExportar=function(){if(!st.base)return;const data=computed(),rows=selected(data.all),head=['RECURSO','Banda','Conceptos','Facturable','Cargabilidad','Capacidad Disponible','Tecnología','Delivery Manager','ID Proyecto','Proyecto','Inicio','Fin','Total mes',...data.days.map(date)],csv=[head,...rows.map(f=>[f.recurso,f.banda,f.concepto,f.regla&&f.regla.facturable,f.regla&&f.regla.cargabilidad,f.regla&&f.regla.capacidad,f.tecnologia,f.manager,f.idProyecto,f.proyecto,f.inicio,f.fin,f.total,...f.values])].map(row=>row.map(v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"').join(',')).join('\r\n');const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='Capacidad_instalada_'+st.mes+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  window.ciAbrir();
})();
