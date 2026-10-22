// @ts-check
// Cuenta: pide el resumen a la API, arma indicadores, graficas y tabla, y va
// completando las horas de Clockify por lotes.
import { apiGet } from '#app/data/api-client.js';
import { withReturn } from '#app/data/navigation.js';
import { readParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatDate } from '#app/lib/format.js';
import { mountAgreements } from '#app/ui/agreements.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderAlerts, renderOpportunities } from './sections/alerts.js';
import { renderCharts } from './sections/charts.js';
import { openBacklog, openBudget, openNps, openRoc } from './sections/dialogs.js';
import { renderFinance } from './sections/finance.js';
import { renderKpis } from './sections/kpis.js';
import { createProjectsTable } from './sections/projects.js';

const PERIOD_KEYS = ['periodo', 'anio', 'mes', 'trimestre', 'desde', 'hasta'];

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const content = byId('cuenta-content');
const errorBox = byId('cuenta-error');
const subtitle = byId('cuenta-subtitle');
const client = /** @type {string} */ (content.dataset.client);
const compare = /** @type {HTMLAnchorElement} */ (byId('cuenta-compare'));
compare.href = withReturn(compare.href);

const params = readParams();
const period = Object.fromEntries(PERIOD_KEYS.filter((key) => params.has(key)).map((key) => [key, /** @type {string} */ (params.get(key))]));

const top = el('div');
const finance = el('div');
const grid = el('div', { class: 'cuenta-grid' });
const list = el('div');
const agreements = el('div');
const progress = el('p', { class: 'note', id: 'cuenta-refresh', role: 'status', 'aria-live': 'polite' });
const table = createProjectsTable(list, '');
let tableReady = false;

/** @type {any} */
let data = null;
/** @type {import('#app/lib/account-metrics.js').AccountProject[]} */
let projects = [];

/** Repinta lo que depende de las horas; la tabla conserva busqueda y pagina. */
function draw() {
  top.replaceChildren();
  grid.replaceChildren();
  renderKpis(top, data, projects, () => openRoc(data.roc));
  renderCharts(grid, projects, { budget: () => openBudget(projects), nps: () => openNps(projects) });
  renderAlerts(grid, projects);
  renderOpportunities(grid, data.opportunities, () => openBacklog(data.opportunities));
  table.update(projects);
}

/** Pide las horas pendientes de tres en tres hasta terminar. */
async function loadConsumption() {
  const pending = projects.filter((p) => p.clockify_pending).map((p) => p.id);
  if (!pending.length) return;
  progress.textContent = 'Consultando horas de Clockify…';
  try {
    let offset = 0;
    for (;;) {
      const { data: batch } = await apiGet('screens/cuenta/consumos/', { nombre: client, offset, pending_id: pending });
      if (!batch.ok) throw new Error('Consumo no disponible');
      for (const item of batch.items) {
        const project = projects.find((p) => p.id.toLowerCase() === String(item.id).toLowerCase());
        if (!project) continue;
        const failed = Boolean(item.error) || typeof item.burn !== 'number' || !Number.isFinite(item.burn);
        project.burn = failed ? null : item.burn;
        project.clockify_pending = false;
        project.clockify_error = failed;
      }
      draw();
      if (batch.next === null || batch.next >= batch.total) break;
      offset = batch.next;
    }
    progress.textContent = 'Horas actualizadas';
  } catch (_) {
    progress.textContent = 'No se pudo completar Clockify. Se conserva el corte disponible.';
  }
}

/** @param {any} body */
function show(body) {
  const { meta } = body;
  data = body.data;
  errorBox.replaceChildren();
  if (!data.available) {
    clearState(content);
    errorBox.append(el('div', { class: 'err', text: data.error }));
    return;
  }
  const cutoff = formatDate(meta.cutoff);
  subtitle.textContent = `Portafolio, satisfacción y horas de la cuenta${cutoff ? ` · Corte ${cutoff}` : ''}`;
  if (data.warning) errorBox.append(el('div', { class: 'err', text: data.warning }));
  projects = data.projects;
  clearState(content);
  if (!tableReady) {
    tableReady = true;
    table.setProjectUrl(/** @type {string} */ (content.dataset.projectUrl));
  }
  content.append(top, finance, grid, list, progress, agreements);
  draw();
  renderFinance(finance, client, period);
  mountAgreements(agreements, { account: client });
  loadConsumption();
}

async function load() {
  showLoading(content, 'Consultando la cuenta…');
  try {
    show(await apiGet('screens/cuenta/', { nombre: client }));
  } catch (error) {
    errorBox.replaceChildren();
    showError(content, error, { onRetry: load });
  }
}

load();
