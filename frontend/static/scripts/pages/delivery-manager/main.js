// @ts-check
// Delivery Manager: primero proyectos y estados; la inversion y las horas de
// Clockify llegan despues, cada una en su propia consulta.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderHours } from './sections/hours.js';
import { renderProjects } from './sections/projects.js';
import { renderSummary } from './sections/summary.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const root = byId('dm-root');
const errorBox = byId('dm-error');
const kpis = byId('dm-kpis');
const table = byId('dm-table');
const monthly = byId('dm-monthly');
const regions = { title: byId('dm-title'), sub: byId('dm-sub'), avatar: byId('dm-avatar'), crumb: byId('dm-crumb'), kpis };
const slug = /** @type {string} */ (root.dataset.slug);
const urls = { project: /** @type {string} */ (root.dataset.projectUrl), account: /** @type {string} */ (root.dataset.accountUrl) };
const endpoint = `screens/delivery-managers/${encodeURIComponent(slug)}/`;

/** @param {string} id @param {string} text */
function fail(id, text) {
  byId(id).prepend(el('div', { class: 'err', role: 'alert' }, `${text} `, el('a', { href: location.pathname, text: 'Reintentar' })));
}

async function load() {
  showLoading(table, 'Cargando proyectos, avance y riesgos…');
  kpis.setAttribute('aria-busy', 'true');
  let data;
  try {
    ({ data } = await apiGet(endpoint, { bloque: 'base' }));
  } catch (error) {
    errorBox.replaceChildren();
    clearState(kpis);
    showError(table, error, { onRetry: load });
    return;
  }
  errorBox.replaceChildren();
  renderSummary(regions, data);
  clearState(table);
  renderProjects(table, data, urls);
  renderHours(monthly, data.name, { state: 'pending' });

  // Inversion y horas se piden a la vez; cada una pinta lo suyo al llegar.
  const investment = apiGet(endpoint, { bloque: 'inv' }).then(({ data: next }) => {
    renderSummary(regions, next);
    renderProjects(table, next, urls);
  });
  const hours = apiGet(endpoint, { bloque: 'horas' }).then(({ data: next }) => renderHours(monthly, next.name, next.hours));
  await Promise.all([
    investment.catch(() => fail('dm-table', 'No se pudo cargar la inversión y los riesgos.')),
    hours.catch(() => fail('dm-monthly', 'No se pudo cargar el consumo de horas.')),
  ]);
}

load();
