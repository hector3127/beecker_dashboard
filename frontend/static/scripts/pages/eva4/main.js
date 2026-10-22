// @ts-check
// EVA-04: une el selector de mes, la API y las secciones de la pantalla.
import { apiGet } from '#app/data/api-client.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatDateTime } from '#app/lib/format.js';
import { createMonthPicker } from '#app/ui/month-picker.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderClients } from './sections/clients.js';
import { renderProcesses } from './sections/processes.js';
import { renderRenewals } from './sections/renewals.js';

const DEFAULT_SUBTITLE = 'Servicios de automatización · clientes, renovaciones y procesos';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const subtitle = byId('eva4-subtitle');
const errorBox = byId('eva4-error');
const filters = byId('eva4-filters');
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
const count = el('p', { id: 'eva4-count', class: 'note eva4-count', role: 'status', 'aria-live': 'polite' });
const picker = createMonthPicker(pickerConfig, {
  label: 'Mes de consumo',
  ariaLabel: 'Consultar consumo por mes',
  onChange(value) {
    writeParams({ mes: value }, { push: true });
    load();
  },
});
filters.append(picker.element, search, count);

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

/** @param {any} data */
function render(data) {
  const { summary } = data;
  subtitle.textContent = data.available
    ? `${summary.active} procesos activos · ${summary.renewal_count} por renovar`
    : DEFAULT_SUBTITLE;
  errorBox.replaceChildren();
  if (data.error) {
    const note = data.available ? ' Se conserva el último corte disponible.' : '';
    errorBox.append(el('div', { class: 'err', text: data.error + note }));
  }
  clearState(content);
  search.hidden = count.hidden = !data.available;
  processes = null;
  if (data.available) {
    processes = renderProcesses(content, data);
    renderRenewals(content, data);
    renderClients(content, data);
    applySearch();
  }
  source.textContent = sourceNote(data);
}

let controller = new AbortController();

async function load() {
  controller.abort(); // elegir otro mes cancela la consulta anterior
  controller = new AbortController();
  const { signal } = controller;
  picker.setBusy(true);
  showLoading(content, 'Consultando el mes…');
  try {
    const body = await apiGet('screens/eva4/', { mes: readParams().get('mes') }, { signal });
    render(body.data);
  } catch (error) {
    if (signal.aborted) return;
    errorBox.replaceChildren();
    showError(content, error, { onRetry: load });
  } finally {
    if (!signal.aborted) picker.setBusy(false);
  }
}

// El boton de regreso del navegador vuelve al mes anterior sin recargar.
addEventListener('popstate', () => {
  picker.setValue(readParams().get('mes') || pickerConfig.value);
  load();
});

load();
