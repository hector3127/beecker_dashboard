// @ts-check
// Margen vendido vs. real: une la API, el periodo de la URL y las secciones.
import { apiGet, apiSend } from '#app/data/api-client.js';
import { readParams } from '#app/data/url-state.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { bindPeople } from './sections/people.js';
import { renderMethod, renderSummary } from './sections/summary.js';
import { renderResults } from './sections/table.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const content = byId('margins-content');
const status = byId('opportunity-status');
const refresh = /** @type {HTMLButtonElement} */ (byId('opportunity-refresh'));
const dates = /** @type {HTMLFormElement} */ (byId('opportunity-dates'));
const POLL_MS = 5000;

/** Los filtros de la URL que entiende la API (sin la vista ni el regreso). */
function filters() {
  const params = readParams();
  /** @type {Record<string, string>} */
  const out = {};
  for (const key of ['nombre', 'periodo', 'anio', 'mes', 'trimestre', 'desde', 'hasta']) {
    const value = params.get(key);
    if (value) out[key] = value;
  }
  return out;
}

/** @type {ReturnType<typeof setInterval> | null} */
let timer = null;

function stopWatching() {
  if (timer) clearInterval(timer);
  timer = null;
}

async function poll() {
  try {
    const { data } = await apiGet('screens/margenes/actualizar/');
    if (data.state === 'ready') {
      stopWatching();
      if (data.has_financial_cut) location.reload();
      else {
        status.textContent = 'No se pudo preparar el corte financiero. Puedes reintentar.';
        refresh.disabled = false;
      }
    } else if (data.state === 'failed') {
      stopWatching();
      status.textContent = 'No se completó la consulta. Se conserva el corte disponible.';
      refresh.disabled = false;
    }
  } catch (_) {
    stopWatching();
    status.textContent = 'No se pudo consultar la actualización.';
    refresh.disabled = false;
  }
}

function watch() {
  refresh.disabled = true;
  status.textContent = 'Consultando costos del periodo…';
  timer = setInterval(poll, POLL_MS);
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
  /** @type {HTMLInputElement} */ (dates.elements.namedItem('desde')).value = meta.start;
  /** @type {HTMLInputElement} */ (dates.elements.namedItem('hasta')).value = meta.end;
  clearState(content);
  content.append(renderMethod(meta.excluded), ...renderSummary(data.summary));
  const results = renderResults(data.opportunities, data.accounts || []);
  content.append(results);
  bindPeople(results, filters);
  if (meta.preparing) {
    status.textContent = 'Preparando costos del periodo… Se conserva el corte disponible.';
    watch();
  }
}

async function load() {
  showLoading(content, 'Consultando oportunidades…');
  try {
    render(await apiGet('screens/margenes/', filters()));
  } catch (error) {
    showError(content, error, { onRetry: load });
  }
}

load();
