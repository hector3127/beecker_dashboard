// @ts-check
// Detalle de costos por proyecto: resumen del corte, tabla con filtros y
// desglose de personas y tarifas bajo demanda.
import { apiGet } from '#app/data/api-client.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { plain } from '#app/lib/format.js';
import { watchLoadingMessages } from '#app/ui/portal-loading.js';
import { renderDetail } from './sections/details.js';
import { fmt, marginColor, marginText, money } from './sections/format.js';

watchLoadingMessages();
/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const { account = '', projectUrl = '' } = byId('cost-page-data').dataset;
const body = byId('cost-audit-body');
const search = /** @type {HTMLInputElement} */ (byId('cost-search'));
const filter = /** @type {HTMLSelectElement} */ (byId('cost-filter'));
let size = 10;
let sortKey = '';
let descending = false;
const bandFilter = /** @type {HTMLSelectElement} */ (byId('cost-band-filter'));
const PERIOD_KEYS = ['periodo', 'anio', 'trimestre', 'mes', 'desde', 'hasta'];
/** @type {any[]} */
let rows = [];
let page = 1;
/** @type {Record<string, any>} */
let preparedDetails = {};
/** @type {ReturnType<typeof setInterval> | null} */
let preparationTimer = null;
function restoreFilters() {
  const params = readParams();
  search.value = params.get('buscar') || '';
  filter.value = ['all','complete','partial','pending','future'].includes(params.get('estado')) ? params.get('estado') : 'all';
  bandFilter.dataset.initialValue = params.get('banda') || '';
  page = Math.max(1, Number.parseInt(params.get('pagina') || '1',10) || 1);
  size = [10,25,50,100].includes(Number(params.get('tamano'))) ? Number(params.get('tamano')) : 10;
  byId('cost-page-size').value = String(size);
  sortKey = ['id','name','hours','cost','revenue','margin','state'].includes(params.get('orden')) ? params.get('orden') : '';
  descending = params.get('sentido') === 'desc';
}
restoreFilters();

/** El periodo de la URL, solo si se eligio uno. */
function period() {
  /** @type {Record<string, string>} */
  const out = {};
  const params = new URLSearchParams(location.search);
  if (!params.has('periodo')) return out;
  for (const key of PERIOD_KEYS) if (params.has(key)) out[key] = /** @type {string} */ (params.get(key));
  return out;
}
/** @param {string} path @param {Record<string, string>} [extra] */
const get = async (path, extra = {}) => (await apiGet(path, { ...(account ? { nombre: account } : {}), ...period(), ...extra })).data;

/** @param {string} id */
function projectLink(id) {
  const target = new URL(projectUrl.replace('project-placeholder', encodeURIComponent(id)), location.href);
  target.searchParams.set('volver', location.pathname + location.search);
  return target.pathname + target.search;
}

/** @param {any} p */
function projectCell(p) {
  if (p.future) return el('span', { text: p.id });
  if (p.cost !== null && p.cost !== undefined && !p.error) return el('a', { class: 'cost-project-link', href: projectLink(p.id), 'aria-label': `Ver proyecto ${p.id}`, text: p.id });
  return el('button', { type: 'button', class: 'cost-project-unavailable', 'data-project-unavailable': p.id, 'data-project-error': p.error || 'La consulta de este proyecto está pendiente.', text: p.id });
}

/** @param {any} p */
function statePill(p) {
  const kind = p.future ? 'future' : p.cost === null || p.cost === undefined ? 'error' : p.complete ? (p.hours === 0 ? 'no-hours' : '') : 'partial';
  const label = p.future ? 'Futuro' : p.cost === null || p.cost === undefined ? 'Sin consultar / error' : p.complete ? (p.hours === 0 ? 'Sin horas en el periodo' : 'Calculado') : 'Costo parcial';
  const note = !p.complete && !p.future ? [el('small', { class: 'audit-error', text: p.cost === null || p.cost === undefined ? p.error || 'Pendiente de consultar Clockify' : 'Falta banda o tarifa' })] : [];
  return [el('span', { class: `audit-pill ${kind}`.trim(), text: label }), ...note];
}

/** @param {any} p */
function projectRow(p) {
  const margin = el('td', { class: 'cost-number', title: p.margin_provisional ? 'Margen provisional: costos incompletos' : 'Margen = (revenue − costo) ÷ revenue', text: p.future ? '—' : marginText(p) });
  margin.style.fontWeight = '700';
  margin.style.color = marginColor(p);
  return [
    el(
      'tr',
      {},
      el('td', { class: 'project-id' }, projectCell(p)),
      el('td', { class: 'cost-project-name', text: p.name || 'Proyecto sin configurar' }),
      el('td', { class: 'cost-number', text: p.future ? '—' : fmt(p.hours) }),
      el('td', { class: 'cost-number', text: p.future ? '—' : p.cost === null || p.cost === undefined ? 'Pendiente' : money(p.cost) }),
      el('td', { class: 'cost-number', text: p.revenue === null || p.revenue === undefined ? 'Sin datos' : money(p.revenue) }),
      margin,
      el('td', {}, ...statePill(p)),
      el('td', {}, el('button', { type: 'button', 'data-persons': p.id, disabled: p.future || null, text: 'Ver personas y tarifas' })),
    ),
    el('tr', { class: 'audit-detail-row', hidden: true }, el('td', { colspan: 8 }, el('div', { class: 'audit-detail' }))),
  ];
}

/** Bandas disponibles en los desgloses del mismo corte. */
function bandsFor(p) {
  return [...new Set((preparedDetails[String(p.id).toLowerCase()]?.people || []).map(person => String(person.band || '').trim()).filter(Boolean))];
}
function populateBands() {
  const selected = bandFilter.dataset.initialValue ?? bandFilter.value;
  delete bandFilter.dataset.initialValue;
  const values = [...new Set(rows.flatMap(bandsFor))].sort((a,b) => a.localeCompare(b, 'es'));
  bandFilter.replaceChildren(el('option', {value:'',text:'Todas las bandas'}),
    ...values.map(value => el('option', {value,text:value})),
    el('option', {value:'__unknown__',text:'Sin banda / sin datos'}));
  bandFilter.value = values.includes(selected) || selected === '__unknown__' ? selected : '';
}
function filteredRows() {
  const wanted = plain(search.value).trim();
  const state = filter.value;
  const filtered = rows.filter(p =>
    plain(`${p.id} ${p.name || ''} ${p.description || ''}`).includes(wanted) &&
    (!bandFilter.value || (bandFilter.value === '__unknown__' ? !(preparedDetails[String(p.id).toLowerCase()]?.people || []).length || (preparedDetails[String(p.id).toLowerCase()]?.people || []).some(person => !String(person.band || '').trim()) : bandsFor(p).includes(bandFilter.value))) &&
    (state === 'all' || (state === 'future' && p.future) || (state === 'pending' && p.cost == null && !p.future) || (state === 'complete' && p.cost != null && p.complete) || (state === 'partial' && p.cost != null && !p.complete)));
  const value = p => sortKey === 'state' ? p.future ? 'Futuro' : p.cost == null ? 'Sin consultar / error' : p.complete ? 'Calculado' : 'Costo parcial' : p[sortKey];
  if (sortKey) filtered.sort((a,b) => {
    const x = value(a), y = value(b);
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    return (typeof x === 'number' && typeof y === 'number' ? x-y : String(x).localeCompare(String(y),'es',{numeric:true,sensitivity:'base'})) * (descending ? -1 : 1);
  });
  return filtered;
}
function render() {
  const filtered = filteredRows();
  const pages = Math.max(1, Math.ceil(filtered.length / size));
  page = Math.min(page, pages);
  writeParams({buscar:search.value.trim(),estado:filter.value === 'all' ? '' : filter.value,
    banda:bandFilter.value,pagina:page > 1 ? page : '',tamano:size !== 10 ? size : '',orden:sortKey,sentido:sortKey ? descending ? 'desc' : 'asc' : ''});
  body.replaceChildren(...filtered.slice((page - 1) * size, page * size).flatMap(projectRow));
  if (!filtered.length) body.append(el('tr', {}, el('td', {colspan:8,class:'cost-empty',text:'No hay proyectos para estos filtros.'})));
  byId('cost-page-label').textContent = `Mostrando ${filtered.length ? (page - 1) * size + 1 : 0}–${Math.min(page * size, filtered.length)} de ${filtered.length} resultados`;
  byId('cost-prev').disabled = page === 1;
  byId('cost-next').disabled = page >= pages;
  const numbers = [...new Set([1,pages,...Array.from({length:5},(_,i) => page+i-2).filter(n => n>=1 && n<=pages)])].sort((a,b)=>a-b);
  const buttons = [];
  numbers.forEach((n,index) => {
    if (index && n > numbers[index-1]+1) buttons.push(el('span', {class:'cost-page-gap',text:'…'}));
    buttons.push(el('button', {type:'button','aria-label':`Página ${n}`,'aria-current':n===page ? 'page' : null,
      text:String(n),onclick:()=>{page=n;render();}}));
  });
  byId('cost-pages').replaceChildren(...buttons);
  document.querySelectorAll('[data-cost-sort]').forEach(button => {
    const active = button.dataset.costSort === sortKey;
    button.closest('th').setAttribute('aria-sort', active ? descending ? 'descending' : 'ascending' : 'none');
    button.querySelector('span').textContent = active ? descending ? '↓' : '↑' : '↕';
  });
  byId('cost-export').disabled = !filtered.length;
}

/** El resumen global con el corte actual. @param {any} data */
function summary(data) {
  const consulted = data.consulted ?? rows.length - data.pending - (data.future || 0);
  byId('cost-summary-label').textContent = data.complete ? 'Costo global' : 'Costo parcial calculado';
  byId('cost-total').textContent = money(data.cost);
  byId('cost-consulted').textContent = `${consulted} de ${rows.length}`;
  byId('cost-pending').textContent = data.pending;
  byId('cost-entries').textContent = fmt(data.deduplicated_entries);
  byId('cost-consulted-percent').textContent = `${rows.length ? (consulted / rows.length * 100).toFixed(1) : '0.0'}% del total`;
  byId('cost-progress').value = rows.length ? Math.min(100, Math.max(0, consulted / rows.length * 100)) : 0;
  byId('cost-pending-percent').textContent = `${rows.length ? (data.pending / rows.length * 100).toFixed(1) : '0.0'}% del total`;
  byId('cost-band-month').textContent = data.band_month ? `Bandas al ${data.band_month}` : '';
  return consulted;
}

/** @param {boolean} [force] */
async function refresh(force = false) {
  byId('cost-refresh').disabled = true;
  byId('cost-refresh-top').disabled = true;
  try {
    const data = await get('costs/summary/', force ? { actualizar: '1' } : {});
    rows = data.projects;
    preparedDetails = data.prepared_details || {};
    populateBands();
    if (data.preparing && !preparationTimer) {
      preparationTimer = setInterval(async () => {
        try {
          const state = (await apiGet('screens/executive/actualizar/', period())).data;
          if (state.state === 'ready' || state.state === 'failed') {
            if (preparationTimer) clearInterval(preparationTimer);
            preparationTimer = null;
            await refresh(true);
          }
        } catch (_) {
          if (preparationTimer) clearInterval(preparationTimer);
          preparationTimer = null;
          byId('cost-note').textContent = 'No se completó la preparación automática. Se conserva el corte disponible.';
        }
      }, 5000);
    }
    const consulted = summary(data);
    byId('cost-updated').textContent = `Hoy, ${new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}`;
    byId('cost-note').textContent = `${consulted} de ${rows.length} proyectos consultados · ${data.pending} pendientes · banda ${data.band_month} · ${data.deduplicated_entries} registros unicos`;
    render();
  } catch (error) {
    byId('cost-total').textContent = error instanceof Error ? error.message : 'No se pudo consultar';
  } finally {
    byId('cost-refresh').disabled = false;
    byId('cost-refresh-top').disabled = false;
  }
}

/** Actualiza la fila de un proyecto con su desglose recien consultado. @param {HTMLTableRowElement} row @param {any} data */
function updateRow(row, data) {
  const index = rows.findIndex((p) => p.id.toLowerCase() === String(data.id).toLowerCase());
  if (index === -1) return;
  rows[index] = { ...rows[index], ...data, error: data.error || '' };
  const p = rows[index];
  const [id, name, hours, cost, revenue, margin, state] = row.cells;
  name.textContent = p.name || 'Proyecto sin configurar';
  id.replaceChildren(projectCell(p));
  hours.textContent = fmt(p.hours);
  cost.textContent = p.cost === null || p.cost === undefined ? 'Pendiente' : money(p.cost);
  revenue.textContent = p.revenue === null || p.revenue === undefined ? 'Sin datos' : money(p.revenue);
  margin.textContent = marginText({ ...p, margin_provisional: !p.complete });
  margin.style.color = marginColor(p);
  margin.title = p.complete ? 'Margen = (revenue − costo) ÷ revenue' : 'Margen provisional: costos incompletos';
  state.replaceChildren(...statePill(p));

}

body.addEventListener('click', async (event) => {
  const unavailable = /** @type {HTMLElement | null} */ (/** @type {Element} */ (event.target).closest('[data-project-unavailable]'));
  if (unavailable) {
    const notice = byId('cost-project-notice');
    notice.textContent = `No es posible abrir el proyecto ${unavailable.dataset.projectUnavailable}. ${unavailable.dataset.projectError}`;
    notice.hidden = false;
    notice.scrollIntoView({ block: 'nearest' });
    return;
  }
  const button = /** @type {HTMLButtonElement | null} */ (/** @type {Element} */ (event.target).closest('[data-persons]'));
  if (!button) return;
  const row = /** @type {HTMLTableRowElement} */ (button.closest('tr'));
  const detail = /** @type {HTMLElement} */ (row.nextElementSibling);
  const target = /** @type {HTMLElement} */ (detail.querySelector('.audit-detail'));
  if (!detail.hidden) {
    detail.hidden = true;
    button.textContent = 'Ver personas y tarifas';
    return;
  }
  detail.hidden = false;
  button.textContent = 'Ocultar detalle';
  if (target.dataset.loaded === 'true') return;
  target.textContent = 'Consultando...';
  button.disabled = true;
  try {
    const prepared = preparedDetails[String(button.dataset.persons).toLowerCase()];
    const data = prepared || (await get('costs/project/', { id: /** @type {string} */ (button.dataset.persons) }));
    preparedDetails[String(data.id).toLowerCase()] = data;
    populateBands();
    target.dataset.loaded = 'true';
    updateRow(row, data);
    target.replaceChildren(...renderDetail(data));
    if (!data.people.length) target.textContent = 'No hay horas en Clockify para el periodo seleccionado.';
    if (!prepared) {
      try {
        const all = await get('costs/summary/');
        const consulted = all.projects.length - all.pending;
        summary({ ...all, consulted });
        byId('cost-note').textContent = `${consulted} de ${all.projects.length} proyectos consultados · ${all.pending} pendientes · Incluye los costos parciales disponibles.`;
      } catch (_) {
        byId('cost-note').textContent = 'Detalle actualizado. No se pudo actualizar el total; pulsa Actualizar resumen.';
      }
    }
  } catch (error) {
    target.textContent = error instanceof Error ? error.message : 'No se pudo consultar';
  } finally {
    button.disabled = false;
  }
});

byId('cost-prev').addEventListener('click', () => {
  page -= 1;
  render();
});
byId('cost-next').addEventListener('click', () => {
  page += 1;
  render();
});
for (const control of [search, filter, bandFilter]) {
  control.addEventListener('input', () => {
    page = 1;
    render();
  });
}
byId('cost-refresh').addEventListener('click', () => refresh(false));
byId('cost-refresh-top').addEventListener('click', () => refresh(false));
byId('cost-page-size').addEventListener('change', event => {size=Number(event.target.value);page=1;render();});
for (const button of document.querySelectorAll('[data-cost-sort]')) button.addEventListener('click', () => {
  descending = sortKey === button.dataset.costSort && !descending;
  sortKey = button.dataset.costSort;page=1;render();
});
byId('cost-export').addEventListener('click', () => {
  const quote = value => {
    let text = String(value ?? '');
    if (/^[=+@\t\r]/.test(text) || /^-(?![0-9])/.test(text)) text = "'"+text;
    return '"'+text.replaceAll('"','""')+'"';
  };
  const records = filteredRows().map(p => [p.id,p.name || '',p.future ? '' : p.hours,p.future ? '' : p.cost,p.revenue,p.margin,p.gross_profit,p.future ? 'Futuro' : p.cost == null ? 'Sin consultar / error' : p.complete ? 'Calculado' : 'Costo parcial',bandsFor(p).join(', ')]);
  const csv = [['Project ID','Proyecto','Horas','Costo (USD)','Revenue (USD)','Margen bruto (%)','Utilidad bruta (USD)','Estado','Bandas'],...records].map(row=>row.map(quote).join(',')).join('\r\n');
  const href = URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8;'}));
  const link = el('a',{href,download:`detalle-costos-${new Date().toLocaleDateString('en-CA')}.csv`});
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(href),1000);
});
addEventListener('popstate', () => {restoreFilters();populateBands();render();});
refresh();
