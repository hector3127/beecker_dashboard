// @ts-check
// Cinco indicadores de la cuenta.
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { averageProgress, hourTotals } from '#app/lib/account-metrics.js';

/**
 * @param {string} title
 * @param {string} value
 * @param {string} note
 * @param {string} [tone]
 */
const kpi = (title, value, note, tone = '') =>
  el('div', { class: 'card cuenta-kpi' }, el('small', { text: title }), el('strong', { class: tone, text: value }), el('p', { class: 'note', text: note }));

/** @param {number} value */
const hours = (value) => `${formatNumber(value, 1)} h`;

/**
 * @param {HTMLElement} container
 * @param {any} data Datos de la API.
 * @param {import('#app/lib/account-metrics.js').AccountProject[]} projects
 */
export function renderKpis(container, data, projects) {
  const progress = averageProgress(projects);
  const totals = hourTotals(projects);
  const over = totals.ratio !== null && totals.ratio > 100;
  container.append(
    el(
      'section',
      { class: 'cuenta-kpis', 'aria-label': 'Indicadores de la cuenta' },
      kpi('Satisfacción del cliente', data.nps == null ? '—' : `${data.nps} NPS`, `${data.nps_sample} proyectos con NPS`),
      kpi('Avance promedio de proyectos', progress == null ? '—' : `${formatNumber(progress, 1)}%`, 'Consumo / presupuesto · corte disponible'),
      kpi('Total de proyectos', String(projects.length), 'Histórico y MPB de la cuenta'),
      kpi('Procesos activos en ROC', String(data.roc_active), 'Procesos de esta cuenta'),
      kpi(
        'Consumo presupuestal',
        totals.ratio === null ? '—' : `${Math.round(totals.ratio)}%`,
        `${hours(totals.burn)} de ${hours(totals.budget)}`,
        over ? 'bad' : 'good',
      ),
    ),
  );
}
