// @ts-check
// Metodologia y los cinco promedios de la comparativa de margenes.
import { el } from '#app/lib/dom.js';

/** @param {number | null | undefined} value @param {string} [unit] */
const oneDecimal = (value, unit = '%') =>
  value === null || value === undefined ? 'Pendiente' : `${value.toFixed(1)}${unit}`;

/** @param {string} symbol @param {string} className @param {Node[]} body */
const metric = (symbol, className, body) =>
  el(
    'article',
    { class: className },
    el('span', { class: 'summary-symbol', 'aria-hidden': 'true', text: symbol }),
    el('div', {}, ...body),
  );

/** Titulo con salto de linea: "Margen real<br>promedio". @param {string} first @param {string} [second] */
const heading = (first, second) => el('h2', {}, first, ...(second ? [el('br'), second] : []));

/** @param {string} excluded */
export function renderMethod(excluded) {
  return el(
    'details',
    { class: 'opportunity-card opportunity-method' },
    el(
      'summary',
      {},
      el('span', { class: 'summary-symbol', 'aria-hidden': 'true', text: 'ⓘ' }),
      el('strong', { text: 'Bookings, operación y cobranza' }),
    ),
    el(
      'div',
      { class: 'opportunity-method-content' },
      el('strong', {
        text: 'Bookings: valor total reconocido de la oportunidad en DataRevenue, sin limitarlo al periodo seleccionado.',
      }),
      el('small', {
        text: 'Bookings suma Confirmed, Invoiced y Collected, incluidos Factoring, con el alcance de servicios de esta vista. Facturado incluye Invoiced y Collected, incluidos Factoring; Cobrado incluye únicamente Collected y Collected Factoring. Estos dos importes usan la fecha G de DataRevenue dentro del rango elegido; no acreditan por sí solos la fecha de factura o transferencia bancaria. Cifras monetarias en dólares estadounidenses · K = miles · M = millones · B = mil millones.',
      }),
      el('small', {
        text: `Solo en esta comparativa se excluyen ${excluded.toLowerCase()}. Las demás vistas conservan su alcance.`,
      }),
      el('small', {
        text: 'Margen vendido: columna I. Margen real: (revenue del periodo − costos) ÷ revenue del periodo. Se conserva la base actual G/H, incluido Confirmed; no se usa Bookings total ni Cobrado como denominador. Revenue operado usa provisionalmente Fecha Revenue Ajustado (G) como fecha del servicio, dentro del rango y hasta hoy. Esta equivalencia está por validar con Florencia. Desviación: real − vendido, en puntos porcentuales (pp). Costos: horas de Clockify × tarifa interna de banda, incluidas horas no facturables y sin task.',
      }),
      el('small', {
        text: '* Costos parciales: el margen puede variar. Los IDs compartidos muestran una comparación de referencia con su costo disponible total, marcada con *. No es una asignación exclusiva ni se suma entre oportunidades; estas referencias se excluyen de los promedios de margen real y desviación.',
      }),
    ),
  );
}

/** @param {any} summary */
export function renderSummary(summary) {
  const deviation = summary.deviation;
  const tone = deviation < 0 ? 'bad' : deviation > 0 ? 'good' : '';
  const verdict = deviation < 0 ? 'Por debajo del margen' : deviation > 0 ? 'Por encima del margen' : 'Comparativa disponible';
  const metrics = el(
    'section',
    { class: 'opportunity-metrics', 'aria-label': 'Resumen de oportunidades' },
    metric('▤', '', [
      heading('Oportunidades', 'con costos completos'),
      el('strong', { text: `${summary.complete} de ${summary.total}` }),
      el('small', { text: `${summary.complete_pct.toFixed(1)}% del total` }),
    ]),
    metric('%', 'metric-green', [
      heading('Margen vendido', 'promedio'),
      el('strong', { text: oneDecimal(summary.sold) }),
      el('small', { text: `${summary.sold_count} oportunidades con margen` }),
    ]),
    metric('▥', '', [
      heading('Margen real', 'promedio'),
      el('strong', { text: oneDecimal(summary.actual) }),
      el('small', { text: `${summary.actual_count} con costos disponibles · incluye parciales` }),
    ]),
    metric('⚠', 'metric-deviation', [
      heading('Desviación promedio'),
      el('strong', { class: tone, text: oneDecimal(deviation, ' pp') }),
      el('small', { text: `${verdict} · ${summary.deviation_count} oportunidades` }),
    ]),
    metric('◷', '', [
      heading('Pendientes de costo'),
      el('strong', { text: summary.pending }),
      el('small', { text: `${summary.pending_pct.toFixed(1)}% del total` }),
    ]),
  );
  const note = el('p', {
    class: 'opportunity-summary-note',
    text: 'Promedios de oportunidades con dato disponible; la desviación usa ambos márgenes. Las referencias de IDs compartidos quedan fuera de estos promedios.',
  });
  return [metrics, note];
}
