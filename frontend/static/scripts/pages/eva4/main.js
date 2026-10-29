import { icon } from "./report_table.js";
// @ts-check
// EVA-04: une el selector de mes, la API y las secciones de la pantalla.
import { apiGet } from '#app/data/api-client.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatDateTime } from '#app/lib/format.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderClients } from './sections/clients.js';
import { renderProcesses } from './sections/processes.js?v=20261029-no-aer';
import { renderRenewals } from './sections/renewals.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
document.querySelector('.eva4-banner-title').before(icon('gear'));
const errorBox = byId('eva4-error');
const monthInput = /** @type {HTMLInputElement} */ (byId('eva4-month'));
const content = byId('eva4-content');
const source = byId('eva4-source');
const pickerConfig = JSON.parse(/** @type {string} */ (byId('eva4-picker').textContent));

const count = el('p', { id: 'eva4-count', class: 'sr-only', role: 'status', 'aria-live': 'polite' });
monthInput.min = pickerConfig.min;
monthInput.max = pickerConfig.max;
monthInput.value = pickerConfig.value;
const monthDisplay=el('span',{class:'eva4-month-display','aria-hidden':'true'});
monthInput.after(monthDisplay);
function syncMonth(){const match=monthInput.value.match(/^(\d{4})-(\d{2})$/);const date=match?new Date(Number(match[1]),Number(match[2])-1,1):null;const label=date?new Intl.DateTimeFormat('es-MX',{month:'short',year:'numeric'}).format(date).replaceAll('.',''):monthInput.value;monthDisplay.textContent=label?label[0].toUpperCase()+label.slice(1):'Selecciona mes';}
syncMonth();
monthInput.addEventListener('change', () => {
  if (!monthInput.validity.valid) return;
  writeParams({ mes: monthInput.value }, { push: true });
  load();
});

/** @param {any} data */
function sourceNote(data) {
  if (!data.available) return 'Solo lectura.';
  const { hours_origin: origin, hours_source: sheet } = data.notes;
  const hours = origin === 'database' ? '(base de datos)' : `(hoja ${sheet})`;
  const loaded = formatDateTime(data.loaded_at);
  return `Fuentes: ROC (Google Sheets) y horas de Clockify ${hours} · Consumo ${data.month} · Solo lectura${loaded ? ` · ${loaded}` : ''}.`;
}

/** @param {any} summary */
function kpis(summary) {
  const chip=(n,label,name)=>el('article',{class:`eva4-kpi kpi-${name}`},icon(name),el('div',{},el('b',{text:n}),el('span',{text:` ${label}`})));
  return el('div',{class:'eva4-kpis'},chip(summary.total,'procesos','layers'),chip(summary.active,'activos','play'),chip(summary.suspended,'suspendidos','pause'),chip(summary.renewal_count,'renovaciones','renew'));
}

/** @param {any} data */
function render(data) {
  errorBox.replaceChildren();
  if (data.error) {
    const note = data.available ? ' Se conserva el último corte disponible.' : '';
    errorBox.append(el('div', { class: 'err', text: data.error + note }));
  }
  clearState(content);
  if (data.available) {
    content.append(kpis(data.summary));
    const tables = el('div', { class: 'eva4-tables' });
    renderClients(tables, data);
    renderRenewals(tables, data);
    content.append(tables);
    renderProcesses(content, data, [count]);
  }
  source.textContent = sourceNote(data);
}

let controller = new AbortController();

async function load() {
  syncMonth();
  controller.abort(); // elegir otro mes cancela la consulta anterior
  controller = new AbortController();
  const { signal } = controller;
  monthInput.disabled = true;
  showLoading(content, 'Consultando el mes…');
  try {
    const body = await apiGet('screens/eva4/', { mes: readParams().get('mes') }, { signal });
    render(body.data);
  } catch (error) {
    if (signal.aborted) return;
    errorBox.replaceChildren();
    showError(content, error, { onRetry: load });
  } finally {
    if (!signal.aborted) monthInput.disabled = false;
  }
}

// El boton de regreso del navegador vuelve al mes anterior sin recargar.
addEventListener('popstate', () => {
  monthInput.value = readParams().get('mes') || pickerConfig.value;
  load();
});

load();
