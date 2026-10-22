// @ts-check
// Resumen: cinco tarjetas con proyectos, salud e inversion.
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { icon } from '#app/ui/icons.js';

const NO_VALUE = '—';

/**
 * @param {string} id
 * @param {'play'|'pause'|'check'|'target'|'people'} iconName
 * @param {string} tone
 * @param {string} title
 * @param {string | number} value
 * @param {string} [note]
 */
function card(id, iconName, tone, title, value, note = '') {
  return el(
    'div',
    { class: 'ops-metric', id },
    el('div', { class: 'ops-metric-head' }, el('span', { class: `ops-icon ${tone}` }, icon(iconName)), title),
    el('div', { class: 'ops-value', text: value }),
    el('div', { class: 'ops-note', text: note }),
  );
}

/**
 * @param {HTMLElement} root
 * @param {any} view Contrato de Operativa ya combinado.
 */
export function renderMetrics(root, view) {
  const noPortfolio = view.loading || view.portfolio_unavailable;
  const noHealth = noPortfolio || view.consumption_pending;
  const { summary, investment } = view;
  const hours = (/** @type {number | null} */ value) =>
    investment.complete && value !== null ? `${formatNumber(value, 0)} h` : NO_VALUE;
  const note = `Horas de inversión registradas · ${view.filters.service || 'IXB/RaaS, AER y T&M'} activos`;
  root.replaceChildren(
    card('ops-metric-progress', 'play', 'ok', 'Proyectos en ejecución', noPortfolio ? NO_VALUE : summary.in_progress),
    card('ops-metric-paused', 'pause', 'bad', 'Suspendidos', noPortfolio ? NO_VALUE : summary.paused),
    card('ops-metric-on-time', 'check', 'ok', 'En tiempo', noHealth ? NO_VALUE : summary.health.on_time),
    card('ops-investment-operational', 'target', 'violet', 'Inversión operativa', hours(investment.operational), note),
    card('ops-investment-commercial', 'people', 'blue', 'Inversión comercial', hours(investment.commercial), note),
  );
}
