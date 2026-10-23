// @ts-check
// EVA-04: une el selector de mes, la API y las secciones de la pantalla.
import { apiGet } from '#app/data/api-client.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatDateTime } from '#app/lib/format.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderClients } from './sections/clients.js';
import { renderProcesses } from './sections/processes.js';
import { renderRenewals } from './sections/renewals.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const errorBox = byId('eva4-error');
const monthInput = /** @type {HTMLInputElement} */ (byId('eva4-month'));
const content = byId('eva4-content');
const source = byId('eva4-source');
const pickerConfig = JSON.parse(/** @type {string} */ (byId('eva4-picker').textContent));

const search = /** @type {HTMLInputElement} */ (
  el('input', {
    id: 'eva4-search',
    class: 'eva4-filter',
    type: 'search',
    placeholder: 'Buscar cliente, proceso, BOT o responsable',
    'aria-label': 'Buscar procesos por cliente, proceso, BOT o responsable',
  })
);
const count = el('p', { id: 'eva4-count', class: 'sr-only', role: 'status', 'aria-live': 'polite' });
monthInput.min = pickerConfig.min;
monthInput.max = pickerConfig.max;
monthInput.value = pickerConfig.value;
monthInput.addEventListener('change', () => {
  if (!monthInput.validity.valid) return;
  writeParams({ mes: monthInput.value }, { push: true });
  load();
});

/** @type {{filter: (text: string) => {shown: number, total: number}} | null} */
let processes = null;

function applySearch() {
  if (!processes) return;
  const { shown, total } = processes.filter(search.value);
  count.textContent = `${shown} de ${total} procesos activos`;
}
search.addEventListener('input', applySearch);

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
  const chip = (/** @type {number} */ n, /** @type {string} */ label) => el('span', {}, el('b', { text: n }), ` ${label}`);
  return el(
    'div',
    { class: 'eva4-kpis' },
    chip(summary.total, 'procesos'),
    chip(summary.active, 'activos'),
    chip(summary.suspended, 'suspendidos'),
    chip(summary.renewal_count, 'renovaciones'),
  );
}

/** @param {any} data */
function render(data) {
  errorBox.replaceChildren();
  if (data.error) {
    const note = data.available ? ' Se conserva el último corte disponible.' : '';
    errorBox.append(el('div', { class: 'err', text: data.error + note }));
  }
  clearState(content);
  search.hidden = !data.available;
  processes = null;
  if (data.available) {
    content.append(kpis(data.summary));
    const tables = el('div', { class: 'eva4-tables' });
    renderClients(tables, data);
    renderRenewals(tables, data);
    content.append(tables);
    processes = renderProcesses(content, data, [search, count]);
    applySearch();
  }
  source.textContent = sourceNote(data);
}

let controller = new AbortController();

async function load() {
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
