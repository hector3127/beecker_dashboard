// @ts-check
// Cinco indicadores de la comparativa: promedios solo con datos disponibles.
import { el } from '#app/lib/dom.js';
import { formatPercent } from '#app/lib/format.js';

/**
 * @param {string} title
 * @param {string} value
 * @param {string} note
 * @param {string} [tone]
 */
const metric = (title, value, note, tone = '') =>
  el(
    'article',
    { class: 'card mg-metric' },
    el('h2', { text: title }),
    el('strong', { class: tone, text: value }),
    el('small', { text: note }),
  );

/**
 * @param {HTMLElement} container
 * @param {any} summary
 */
export function renderSummary(container, summary) {
  const deviation = summary.deviation;
  const tone = deviation < 0 ? 'bad' : deviation > 0 ? 'good' : '';
  const direction = deviation < 0 ? 'Por debajo del margen' : deviation > 0 ? 'Por encima del margen' : 'Comparativa disponible';
  container.append(
    el(
      'section',
      { class: 'mg-metrics', 'aria-label': 'Resumen de oportunidades' },
      metric('Oportunidades con costos completos', `${summary.complete} de ${summary.total}`, `${formatPercent(summary.complete_pct, '%', 1)} del total`),
      metric('Margen vendido promedio', formatPercent(summary.sold, '%', 1), `${summary.sold_count} oportunidades con margen`),
      metric('Margen real promedio', formatPercent(summary.actual, '%', 1), `${summary.actual_count} con costos disponibles · incluye parciales`),
      metric('Desviación promedio', formatPercent(deviation, ' pp', 1), `${direction} · ${summary.deviation_count} oportunidades`, tone),
      metric('Pendientes de costo', String(summary.pending), `${formatPercent(summary.pending_pct, '%', 1)} del total`),
    ),
    el('p', {
      class: 'note',
      text: 'Promedios de oportunidades con dato disponible; la desviación usa ambos márgenes. Las referencias de IDs compartidos quedan fuera de estos promedios.',
    }),
  );
}
