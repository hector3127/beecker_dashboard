// @ts-check
// Resumen: cinco tarjetas con proyectos, salud e inversion.
import { el, svg } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { icon } from '#app/ui/icons.js';

const NO_VALUE = '—';

/**
 * @param {string} id
 * @param {'play'|'pause'|'check'|'target'|'people'|'chart'|'coins'} iconName
 * @param {string} tone
 * @param {string} title
 * @param {string | number} value
 * @param {string} [note]
 */
function card(id, iconName, tone, title, value, note = '') {
  return el(
    'div',
    { class: 'ops-metric', id },
    el('div', { class: 'ops-metric-head' }, el('span', { class: `ops-icon ${tone}` }, iconName==='coins' ? svg('svg',{viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':1.8,'aria-hidden':'true'},svg('ellipse',{cx:12,cy:5,rx:8,ry:3}),svg('path',{d:'M4 5v14c0 4 16 4 16 0V5M4 10c0 4 16 4 16 0M4 15c0 4 16 4 16 0'})) : icon(iconName)), title),
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
    card('ops-metric-progress', 'play', 'ok', 'Proyectos en ejecución', noPortfolio ? NO_VALUE : summary.in_progress, !noPortfolio && view.portfolio_total ? `${Math.round(summary.in_progress/view.portfolio_total*100)}% del total` : ''),
    card('ops-metric-paused', 'pause', 'bad', 'Suspendidos', noPortfolio ? NO_VALUE : summary.paused, !noPortfolio && view.portfolio_total ? `${Math.round(summary.paused/view.portfolio_total*100)}% del total` : ''),
    card('ops-metric-on-time', 'check', 'blue', 'En tiempo', noHealth ? NO_VALUE : summary.health.on_time, noHealth || !summary.in_progress ? '' : `${summary.on_time_percent}% en ejecución`),
    card('ops-investment-operational', 'coins', 'violet', 'Inversión operativa', hours(investment.operational), note),
    card('ops-investment-commercial', 'chart', 'amber', 'Inversión comercial', hours(investment.commercial), note),
  );
}
