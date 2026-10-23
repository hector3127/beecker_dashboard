// @ts-check
// Cuenta: resumen de la cuenta, horas por lotes, finanzas y acuerdos.
import { apiGet } from '#app/data/api-client.js';
import { readParams } from '#app/data/url-state.js';
import { averageProgress } from '#app/lib/account-summary.js';
import { el } from '#app/lib/dom.js';
import { createAgreements } from '#app/ui/agreements.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { openBudget } from './sections/budget.js';
import { renderGrid, updateAlerts } from './sections/charts.js';
import { openBacklog, openNps, openRoc, renderOpportunities } from './sections/details.js';
import { loadFinance, renderFinance } from './sections/finance.js';
import { renderKpis, updateConsumption } from './sections/kpis.js';
import { createModal } from './sections/modal.js';
import { renderProjects } from './sections/projects.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const app = byId('account');
const content = byId('account-content');
const status = byId('account-refresh');
const { client = '', projectUrl = '', costsUrl = '' } = app.dataset;
const BATCH_FAILED = 'No se pudo completar Clockify. Se conserva el corte disponible.';

/** Los filtros de periodo de la URL, para las finanzas. */
function period() {
  /** @type {Record<string, string>} */
  const out = { nombre: client };
  const params = readParams();
  for (const key of ['periodo', 'anio', 'mes', 'trimestre', 'desde', 'hasta']) {
    const value = params.get(key);
    if (value) out[key] = value;
  }
  return out;
}

/**
 * Las horas llegan de tres en tres; cada lote actualiza tabla, KPI y alertas.
 * @param {any[]} projects
 * @param {{setBurn: (id: string, text: string) => void}} table
 */
async function loadHours(projects, table) {
  const pending = projects.filter((p) => p.clockify_pending).map((p) => p.id);
  try {
    let offset = 0;
    for (;;) {
      const { data } = await apiGet('screens/cuenta/consumos/', { nombre: client, offset, pending_id: pending });
      if (!data.ok) throw new Error('lote');
      for (const item of data.items) {
        const failed = Boolean(item.error) || typeof item.burn !== 'number' || !Number.isFinite(item.burn);
        const project = projects.find((p) => String(p.id).toLowerCase() === String(item.id).toLowerCase());
        if (project) {
          project.burn = failed ? null : item.burn;
          project.clockify_pending = false;
          project.clockify_error = failed ? item.error || 'Consumo no disponible' : '';
        }
        table.setBurn(item.id, failed ? 'No disponible' : `${Number(item.burn).toLocaleString('es-MX')} h`);
      }
      updateConsumption(projects);
      updateAlerts(projects);
      if (data.next >= data.total) break;
      offset = data.next;
    }
    status.textContent = 'Horas actualizadas';
  } catch (_) {
    status.textContent = BATCH_FAILED;
  }
}

/** @param {any} data */
function render(data) {
  const projects = data.projects;
  const detail = createModal();
  const table = renderProjects(projects, projectUrl);
  const opportunities = renderOpportunities(data.opportunities, () => openBacklog(detail, data.opportunities));
  const summary = { progress: averageProgress(projects), total: projects.length };
  clearState(content);
  content.append(
    renderKpis(data, summary, projects, { roc: () => openRoc(detail, data.roc) }),
    renderFinance(costsUrl),
    renderGrid(projects, { budget: () => openBudget(detail, projects), nps: () => openNps(detail, projects) }, opportunities),
    table.section,
    detail.modal,
  );
  updateConsumption(projects);
  updateAlerts(projects);
  loadFinance(period());
  if (data.consumption_pending) loadHours(projects, table);
}

async function load() {
  showLoading(content, 'Consultando la cuenta…');
  try {
    const { data, meta } = await apiGet('screens/cuenta/', { nombre: client });
    byId('account-cutoff').textContent = meta.cutoff || '';
    if (!data.available) {
      clearState(content);
      content.append(el('div', { class: 'account-card', text: data.error }));
      return;
    }
    render(data);
  } catch (error) {
    showError(content, error, { onRetry: load });
  }
}

app.append(createAgreements({ account: client }));
load();
