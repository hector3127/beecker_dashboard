// @ts-check
// Tabla de proyectos del Delivery Manager; los que piden atencion van primero.
import { el } from '#app/lib/dom.js';
import { findAccountLogo, loadAccountLogos } from '#app/lib/account-logos.js';
import { csvCell } from './hours.js';
import { formatNumber } from '#app/lib/format.js';
import { icon } from './kpis.js';

const DASH = '—';
const initial=new URLSearchParams(location.search);
const filters={search:initial.get('dm_buscar')||'',state:initial.get('dm_estado')||'',service:initial.get('dm_servicio')||''};
const normalize=text=>String(text).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
const match=row=>normalize(`${row.project_id} ${row.name} ${row.client} ${row.service}`).includes(normalize(filters.search))&&(!filters.state||row.status_code===filters.state)&&(!filters.service||row.service===filters.service);
function accountLogo(name){
  const text=name.trim().split(/\s+/).slice(0,2).map(word=>word[0]).join('').toUpperCase();
  const host=el('span',{class:'dm-account-logo','aria-hidden':'true',text});
  loadAccountLogos().then(items=>{const logo=findAccountLogo(items,name);if(!logo)return;const img=el('img',{src:logo.url,alt:'',loading:'lazy',decoding:'async'});img.addEventListener('error',()=>host.replaceChildren(text),{once:true});host.replaceChildren(img);});
  return host;
}
export function downloadProjects(data){
  const rows=[HEADERS,...data.rows.filter(match).map(row=>[row.project_id,row.name,row.client,row.service,row.start,row.end,row.budget,row.burn,row.investment_operational,row.investment_commercial,row.status_label,row.progress_percent,row.etc_hours,row.renewal_days,row.risk])];
  const url=URL.createObjectURL(new Blob(['\uFEFF'+rows.map(row=>row.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}));
  el('a',{href:url,download:`proyectos-${data.name}.csv`}).click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function progressCell(value){
  if(value===null||value===undefined)return DASH;
  const tone=value>100?'bad':value>=85?'warning':'good';
  return el('span',{class:`dm-value dm-progress-value ${tone}`,text:`${formatNumber(value,1)}%`});
}
const HEADERS = [
  'ID del proyecto',
  'Proyecto',
  'Cuenta',
  'Servicio',
  'Inicio',
  'Fin',
  'Presupuesto (h)',
  'Consumo (h)',
  'Inv. operativa (h)',
  'Inv. comercial (h)',
  'Estado',
  'Avance',
  'ETC (h)',
  'Renovación (días)',
  'Riesgo abierto',
];

/** @param {number | null | undefined} value */
const hours = (value) => (value === null || value === undefined ? DASH : formatNumber(value, 2));
/** @param {string} template @param {string} placeholder @param {string} value */
const link = (template, placeholder, value) => template.replace(placeholder, encodeURIComponent(value));

/** Etiqueta con color: bueno, advertencia o malo. @param {string} tone @param {string} text */
const value = (tone, text) => el('span', { class: `dm-value ${tone}`, text });

/**
 * @param {any} row
 * @param {{project: string, account: string}} urls
 */
function projectRow(row, urls) {
  const project = link(urls.project, 'project-placeholder', row.project_id);
  const progress = row.progress_percent;
  const num = (/** @type {Node | string} */ content) => el('td', { class: 'num' }, content);
  return el(
    'tr',
    { class: row.row_class || null },
    el('td', {}, el('a', { href: project, text: row.project_id })),
    el('td', {}, el('b', {}, el('a', { href: project, text: row.name }))),
    el(
      'td',
      {},
      row.client ? el('a', { class:'dm-account-link',href: link(urls.account, 'account-placeholder', row.account_slug) },accountLogo(row.client),el('span',{text:row.client})) : 'Sin cuenta',
    ),
    el('td', {},el('span',{class:`dm-service service-${String(row.service).replace(/[^a-z]/gi,'').toLowerCase()}`,text:row.service})),
    el('td', { text: row.start || 'Sin fecha' }),
    el('td', { text: row.end || 'Sin fecha' }),
    num(hours(row.budget)),
    num(hours(row.burn)),
    num(hours(row.investment_operational)),
    num(hours(row.investment_commercial)),
    el(
      'td',
      {},
      el('span', { class: `st s-${row.status_code}` }, el('i'), row.status_label),
      ...(row.detail ? [el('small', { text: row.detail })] : []),
    ),
    num(progressCell(progress)),
    num(row.etc_hours === null ? DASH : value(row.etc_hours <= 0 ? 'bad' : 'good', formatNumber(row.etc_hours, 2))),
    num(row.renewal_days === null ? DASH : value(row.renewal_days < 30 ? 'bad' : 'good', String(row.renewal_days))),
    num(row.risk),
  );
}

/** @param {string} name */
function heading(name) {
  return el(
    'div',
    { class: 'section-head' },
    icon('folder'),
    el('div', {}, el('h2', { text: `Proyectos de ${name}` }), el('div', { class: 'hs', text: 'Los que necesitan atención aparecen primero' })),
  );
}

/** @param {string} name */
export function loadingTable(name) {
  return [heading(name), el('div', { class: 'vacio', role: 'status', text: 'Cargando proyectos, avance y riesgos…' })];
}

/**
 * @param {any} data
 * @param {{project: string, account: string}} urls
 */
export function renderTable(data, urls) {
  const search=el('input',{type:'search',id:'dm-project-search',placeholder:'Buscar proyecto, cuenta o servicio…','aria-label':'Buscar proyectos del DM',value:filters.search});
  const statuses=[...new Map(data.rows.map(row=>[row.status_code,row.status_label])).entries()];
  const services=[...new Set(data.rows.map(row=>row.service))].sort();
  const state=el('select',{'aria-label':'Estado del proyecto',id:'dm-project-state'},el('option',{value:'',text:'Todos los estados'}),...statuses.map(([key,label])=>el('option',{value:key,text:label})));
  const service=el('select',{'aria-label':'Servicio del proyecto',id:'dm-project-service'},el('option',{value:'',text:'Todos los servicios'}),...services.map(name=>el('option',{value:name,text:name})));
  state.value=filters.state;service.value=filters.service;
  const count=el('span',{class:'dm-project-count','aria-live':'polite'});
  const body=el('tbody');
  const table=el('table',{},el('thead',{},el('tr',{},...HEADERS.map(text=>el('th',{text})))),body);
  function draw(){
    filters.search=search.value;filters.state=state.value;filters.service=service.value;
    const visible=data.rows.filter(match);
    body.replaceChildren(...(visible.length?visible.map(row=>projectRow(row,urls)):[el('tr',{},el('td',{colspan:15,class:'vacio',text:data.rows.length?'No hay proyectos que coincidan.':'Sin proyectos en ejecución ni suspendidos.'}))]));
    count.textContent=`${visible.length} de ${data.rows.length} proyectos`;
    const url=new URL(location.href);
    for(const [key,value] of [['dm_buscar',filters.search],['dm_estado',filters.state],['dm_servicio',filters.service]]){if(value)url.searchParams.set(key,value);else url.searchParams.delete(key);}
    history.replaceState(history.state,'',url.pathname+url.search+url.hash);
  }
  search.addEventListener('input',draw);state.addEventListener('change',draw);service.addEventListener('change',draw);
  const clear=el('button',{type:'button',class:'dm-filter-clear',text:'Limpiar',onclick:()=>{search.value='';state.value='';service.value='';draw();}});
  const head=heading(data.name);
  head.append(el('div',{class:'dm-project-controls'},search,state,service,clear));
  draw();
  return [head,count,el('div',{class:'table-scroll'},table)];
}
