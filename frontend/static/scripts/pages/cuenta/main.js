// @ts-check
// Cuenta: pide el resumen a la API y arma indicadores, graficas y tabla.
import { apiGet } from '#app/data/api-client.js';
import { withReturn } from '#app/data/navigation.js';
import { el } from '#app/lib/dom.js';
import { formatDate } from '#app/lib/format.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderAlerts, renderOpportunities } from './sections/alerts.js';
import { renderCharts } from './sections/charts.js';
import { renderKpis } from './sections/kpis.js';
import { createProjectsTable } from './sections/projects.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const content = byId('cuenta-content');
const errorBox = byId('cuenta-error');
const subtitle = byId('cuenta-subtitle');
const client = /** @type {string} */ (content.dataset.client);
const compare = /** @type {HTMLAnchorElement} */ (byId('cuenta-compare'));
compare.href = withReturn(compare.href);

/** Se arma una vez; cada actualizacion de datos solo repinta. */
let table = null;

/** @param {any} data */
function render(data) {
  clearState(content);
  const projects = data.projects;
  const top = el('div', { class: 'cuenta-top' });
  const grid = el('div', { class: 'cuenta-grid' });
  const list = el('div');
  renderKpis(top, data, projects);
  renderCharts(grid, projects);
  renderAlerts(grid, projects);
  renderOpportunities(grid, data.opportunities);
  content.append(top, grid, list);
  table = createProjectsTable(list, /** @type {string} */ (content.dataset.projectUrl));
  table.update(projects);
}

/** @param {any} body */
function show(body) {
  const { data, meta } = body;
  errorBox.replaceChildren();
  if (!data.available) {
    clearState(content);
    errorBox.append(el('div', { class: 'err', text: data.error }));
    return;
  }
  const cutoff = formatDate(meta.cutoff);
  subtitle.textContent = `Portafolio, satisfacción y horas de la cuenta${cutoff ? ` · Corte ${cutoff}` : ''}`;
  if (data.warning) errorBox.append(el('div', { class: 'err', text: data.warning }));
  render(data);
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
