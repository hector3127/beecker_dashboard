// @ts-check
import { apiGet } from '#app/data/api-client.js';
import { config } from '#app/data/config.js';
import { el } from '#app/lib/dom.js';
import { formatNumber, formatDateTime } from '#app/lib/format.js';
import { selectProjects } from './selection.js';

const byId = (/** @type {string} */ id) => /** @type {HTMLElement} */ (document.getElementById(id));
const form = /** @type {HTMLFormElement} */ (byId('hours-filters'));
const year = /** @type {HTMLInputElement} */ (byId('hours-year'));
const mode = /** @type {HTMLSelectElement} */ (byId('hours-period'));
const from = /** @type {HTMLInputElement} */ (byId('hours-from'));
const to = /** @type {HTMLInputElement} */ (byId('hours-to'));
const search = /** @type {HTMLInputElement} */ (byId('hours-search'));
const download = /** @type {HTMLAnchorElement} */ (byId('hours-download'));
const table = byId('hours-table');
const status = byId('hours-status');
const content = byId('hours-content');
const initial = new URLSearchParams(location.search);
const selected = new Set(initial.getAll('proyecto'));
/** @type {any} */
let report = null;
/** @type {Record<string,string>} */
let appliedPeriod = {};
let requestId = 0;
const number = (/** @type {number} */ value) => formatNumber(value, 2);
const normalize = (/** @type {string} */ value) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

/** @param {{hours:number|null,partial:boolean}} cell */
function value(cell) {
  return cell.hours == null ? 'Pendiente' : `${number(cell.hours)}${cell.partial ? '*' : ''}`;
}

function periodFields() {
  const range = mode.value === 'rango';
  byId('hours-range').hidden = !range;
  byId('hours-year-field').hidden = range;
  year.required = !range;
  from.required = to.required = range;
}

function projectOptions() {
  const host = byId('hours-project-options');
  host.replaceChildren();
  if (!report) return;
  const term = normalize(search.value);
  const matches = report.projects.filter((/** @type {any} */ p) => normalize(`${p.id} ${p.name}`).includes(term));
  for (const project of matches) {
    const checkbox = /** @type {HTMLInputElement} */ (el('input', {type:'checkbox',value:project.id,'aria-label':`${project.id} · ${project.name}`}));
    checkbox.checked = selected.has(project.id);
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) selected.add(project.id); else selected.delete(project.id);
      draw();
    });
    host.append(el('label', {class:'hours-project-option'}, checkbox, el('span', {}, el('strong', {text:project.id}), el('small', {text:project.name}))));
  }
  if (!matches.length) host.append(el('p', {class:'note',text:'No hay proyectos para esta búsqueda.'}));
}

function draw() {
  if (!report) return;
  const data = selectProjects(report, selected);
  const url = new URL(location.href);
  for (const key of ['anio','desde','hasta','periodo','proyecto']) url.searchParams.delete(key);
  for (const [key,val] of Object.entries(appliedPeriod)) url.searchParams.set(key,val);
  for (const id of selected) url.searchParams.append('proyecto',id);
  history.replaceState(null,'',url);
  byId('hours-project-summary').textContent = selected.size ? `${selected.size} proyecto${selected.size === 1 ? '' : 's'} seleccionado${selected.size === 1 ? '' : 's'}` : `Todos los proyectos (${report.projects.length})`;
  const headers = [el('th',{scope:'col',text:'Proyecto'}), ...data.months.map((/** @type {any} */ m) => el('th',{scope:'col',class:m.partial?'hours-current':'',text:`${m.label}${m.partial?'*':''}`})), el('th',{scope:'col',text:'Total (h)'})];
  const body = el('tbody');
  for (const project of data.projects) {
    const target = new URL(form.dataset.projectUrl.replace('PROJECT_ID',encodeURIComponent(project.id)),location.origin);
    target.searchParams.set('volver',location.pathname+location.search);
    body.append(el('tr',{},el('th',{scope:'row'},el('a',{href:target.pathname+target.search,text:project.id}),project.name!==project.id?el('small',{text:project.name}):'',project.issue?el('small',{class:'hours-pending',text:project.issue}):''),...project.cells.map((/** @type {any} */ c)=>el('td',{class:c.partial?'hours-pending':'',text:value(c)})),el('td',{text:`${number(project.known_hours)}${project.partial?'*':''}`})));
  }
  if (!data.projects.length) body.append(el('tr',{},el('td',{colspan:data.months.length+2,text:'No hay proyectos identificados para esta cuenta y periodo.'})));
  const footer = el('tfoot',{},el('tr',{},el('th',{scope:'row',text:selected.size?'Total de la selección':'Total de la cuenta'}),...data.totals.map((/** @type {any} */ c)=>el('td',{text:value(c)})),el('td',{text:`${number(data.known_hours)}${data.partial?'*':''}`})));
  table.replaceChildren(el('caption',{class:'sr-only',text:`Horas mensuales de ${data.client}, del ${data.start} al ${data.end}`}),el('thead',{},el('tr',{},...headers)),body,footer);
  byId('hours-count').textContent = `${data.projects.length} de ${report.projects.length} proyectos. Los totales y el CSV corresponden a los proyectos seleccionados. * Total parcial: suma solo horas conocidas.`;
  byId('hours-summary').replaceChildren(...[
    ['Horas conocidas',`${number(data.known_hours)} h${data.partial?'*':''}`],
    ['Proyectos',String(data.projects.length)],
    ['Periodo',`${data.start} a ${data.end}`],
  ].map(([label,text])=>el('p',{},el('span',{text:label}),el('strong',{text}))));
  const csv = new URL(config.apiBase+'screens/cuenta/horas/',location.origin);
  csv.search = new URLSearchParams({nombre:data.client,...appliedPeriod,descargar:'csv'}).toString();
  for (const id of selected) csv.searchParams.append('proyecto',id);
  download.href = csv.href;
  status.textContent = data.partial?'Reporte parcial: hay datos pendientes. Revisa los valores marcados con *.':'Reporte generado.';
}

async function load() {
  const ownRequest = ++requestId;
  const period = mode.value === 'rango' ? {desde:from.value,hasta:to.value} : {anio:year.value};
  const range = mode.value === 'rango';
  download.hidden = true;
  content.hidden = true;
  byId('hours-project-picker').hidden = true;
  status.dataset.error = 'false';
  status.textContent = 'Generando reporte mensual de horas…';
  form.setAttribute('aria-busy','true');
  try {
    const {data} = await apiGet('screens/cuenta/horas/',{nombre:form.dataset.client,...period});
    if (ownRequest !== requestId) return;
    report = data;
    appliedPeriod = range ? {desde:data.start,hasta:data.end} : {anio:String(data.year)};
    if (range) { from.value=data.start; to.value=data.end; }
    const available = new Set(data.projects.map((/** @type {any} */ p)=>p.id));
    for (const id of selected) if (!available.has(id)) selected.delete(id);
    projectOptions();
    draw();
    byId('hours-source').textContent = `Fuente: Clockify sincronizado. ${data.synced_at?`Última sincronización del periodo: ${formatDateTime(data.synced_at)}.`:'No hay meses sincronizados para este periodo.'} El rango incluye ambas fechas. Los meses marcados con * son cortes parciales.`;
    download.hidden = false;
    content.hidden = false;
  } catch (error) {
    if (ownRequest !== requestId) return;
    status.dataset.error = 'true';
    status.textContent = error instanceof Error?error.message:'No se pudo generar el reporte. Intenta de nuevo.';
  } finally {
    if (ownRequest === requestId) {
      form.removeAttribute('aria-busy');
      byId('hours-project-picker').hidden = content.hidden;
    }
  }
}
year.value = initial.get('anio')||form.dataset.year;
mode.value = initial.has('desde')?'rango':'anio';
from.value = initial.get('desde')||`${year.value}-01-01`;
to.value = initial.get('hasta')||form.dataset.today;
periodFields();
mode.addEventListener('change',periodFields);
form.addEventListener('submit',event=>{event.preventDefault();load();});
search.addEventListener('input',projectOptions);
byId('hours-clear-projects').addEventListener('click',()=>{selected.clear();search.value='';projectOptions();draw();});
load();
