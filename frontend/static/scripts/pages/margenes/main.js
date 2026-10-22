// @ts-check
// Comparativa de margenes: une el periodo de la URL, la API y las secciones.
import { apiGet, apiSend } from '#app/data/api-client.js';
import { readParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderOpportunities } from './sections/opportunities.js';
import { renderSummary } from './sections/summary.js';

const POLL_MS = 5000;
const PERIOD_KEYS = ['periodo', 'anio', 'mes', 'trimestre', 'desde', 'hasta'];

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const content = byId('mg-content');
const status = byId('mg-status');
const excluded = byId('mg-excluded');
const refresh = /** @type {HTMLButtonElement} */ (byId('mg-refresh'));

/** El periodo y la cuenta viajan en la URL de la pagina; la API recibe los mismos. */
function pageParams() {
  const params = readParams();
  return Object.fromEntries(PERIOD_KEYS.filter((key) => params.has(key)).map((key) => [key, /** @type {string} */ (params.get(key))]));
}

const search = /** @type {HTMLInputElement} */ (
  el('input', {
    id: 'mg-search',
    type: 'search',
    placeholder: 'Buscar cuenta, oportunidad o Project ID…',
    'aria-label': 'Buscar cuenta, oportunidad o proyecto',
  })
);
const count = el('p', { id: 'mg-count', class: 'note', role: 'status', 'aria-live': 'polite' });

/** @type {{filter: (text: string) => {shown: number, total: number}} | null} */
let table = null;

function applySearch() {
  if (!table) return;
  const { shown, total } = table.filter(search.value);
  count.textContent = `${shown} de ${total} oportunidades`;
}
search.addEventListener('input', applySearch);

/** @type {ReturnType<typeof setInterval> | null} */
let timer = null;

function stopWatching() {
  if (timer) clearInterval(timer);
  timer = null;
  refresh.disabled = false;
}

/** Consulta cada 5 s hasta que el corte este listo; entonces vuelve a pedir los datos. */
function watch() {
  refresh.disabled = true;
  status.textContent = 'Consultando costos del periodo…';
  if (timer) return;
  timer = setInterval(async () => {
    try {
      const { data } = await apiGet('screens/margenes/actualizar/');
      if (data.state === 'ready') {
        stopWatching();
        if (data.has_financial_cut) load();
        else status.textContent = 'No se pudo preparar el corte financiero. Puedes reintentar.';
      } else if (data.state === 'failed') {
        stopWatching();
        status.textContent = 'No se completó la consulta. Se conserva el corte disponible.';
      }
    } catch (_) {
      stopWatching();
      status.textContent = 'No se pudo consultar la actualización.';
    }
  }, POLL_MS);
}

refresh.addEventListener('click', async () => {
  refresh.disabled = true;
  try {
    await apiSend('POST', 'screens/margenes/actualizar/');
    watch();
  } catch (_) {
    refresh.disabled = false;
    status.textContent = 'No se pudo iniciar la actualización.';
  }
});

/** @param {any} body */
function render(body) {
  const { data, meta } = body;
  clearState(content);
  excluded.textContent = `Solo en esta comparativa se excluyen ${String(meta.excluded).toLowerCase()}. Las demás vistas conservan su alcance.`;
  renderSummary(content, data.summary);
  content.append(search, count);
  table = renderOpportunities(content, data.opportunities, pageParams);
  applySearch();
  if (meta.preparing) {
    status.textContent = 'Preparando costos del periodo… Se conserva el corte disponible.';
    watch();
  } else if (!timer) {
    status.textContent = '';
  }
}

async function load() {
  showLoading(content, 'Consultando oportunidades…');
  try {
    render(await apiGet('screens/margenes/', { ...pageParams(), nombre: readParams().get('nombre') }));
  } catch (error) {
    showError(content, error, { onRetry: load });
  }
}

load();
