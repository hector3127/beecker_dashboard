import { icon } from "./report_table.js";
// @ts-check
// EVA-04: consulta el mes actual y presenta las secciones de la pantalla.
import { apiGet } from '#app/data/api-client.js';
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
const content = byId('eva4-content');
const source = byId('eva4-source');
const pickerConfig = JSON.parse(/** @type {string} */ (byId('eva4-picker').textContent));

const count = el('p', { id: 'eva4-count', class: 'sr-only', role: 'status', 'aria-live': 'polite' });

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
  controller.abort(); // elegir otro mes cancela la consulta anterior
  controller = new AbortController();
  const { signal } = controller;
  showLoading(content, 'Consultando el mes…');
  try {
    const body = await apiGet('screens/eva4/', { mes: pickerConfig.value }, { signal });
    render(body.data);
  } catch (error) {
    if (signal.aborted) return;
    errorBox.replaceChildren();
    showError(content, error, { onRetry: load });
  }
}

load();
