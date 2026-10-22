// @ts-check
// Encabezado e indicadores del Delivery Manager.
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';

/** Horas de inversion: «…» mientras llegan, «—» si no se pudieron leer. @param {any} investment @param {'commercial' | 'operational'} key */
function investmentText(investment, key) {
  if (investment.state === 'pending') return '…';
  return investment.state === 'ready' ? `${formatNumber(investment[key])} h` : '—';
}

/**
 * @param {string} title
 * @param {string} value
 * @param {string} note
 */
const kpi = (title, value, note) =>
  el('div', { class: 'card dm-kpi' }, el('div', { class: 'kl', text: title }), el('div', { class: 'kv', text: value }), el('div', { class: 'ke', text: note }));

/**
 * @param {{title: HTMLElement, sub: HTMLElement, avatar: HTMLElement, crumb: HTMLElement, kpis: HTMLElement}} regions
 * @param {any} data
 */
export function renderSummary(regions, data) {
  const { summary, investment } = data;
  const plural = (/** @type {number} */ n, /** @type {string} */ word) => `${n} ${word}${n === 1 ? '' : 's'}`;
  regions.title.textContent = data.name;
  regions.crumb.textContent = data.name;
  regions.avatar.textContent = data.initials;
  regions.sub.textContent = `Delivery Manager · ${plural(summary.total, 'proyecto')} ${summary.total === 1 ? 'asignado' : 'asignados'}`;
  document.title = `Delivery Manager ${data.name}`;
  regions.kpis.removeAttribute('aria-busy');
  regions.kpis.replaceChildren(
    kpi('Proyectos', String(summary.total), `${summary.in_progress} en ejecución y ${plural(summary.paused, 'suspendido')}`),
    kpi('En tiempo', String(summary.health.on_time), `${summary.health.at_risk} en riesgo y ${plural(summary.health.critical, 'crítico')}`),
    kpi('Proyectos críticos', String(summary.health.critical), 'Proyectos activos en estado crítico'),
    kpi('Suspendidos', String(summary.paused), 'Proyectos suspendidos del DM'),
    kpi('Inversión comercial', investmentText(investment, 'commercial'), 'Proyectos en curso, incluidos suspendidos'),
    kpi('Inversión operativa', investmentText(investment, 'operational'), 'Proyectos en curso, incluidos suspendidos'),
  );
}
