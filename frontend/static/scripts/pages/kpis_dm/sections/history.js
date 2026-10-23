// @ts-check
// Historico por mes y por trimestre: TP, T y C de cada Delivery Manager.
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { DASH, days, percent } from './summary.js';

/** Celdas TP, T y C de un corte; sin corte son tres guiones. @param {any} cell @param {boolean} [whole] TP sin decimales (promedio). */
function cells(cell, whole = false) {
  if (!cell) return [el('td', { class: 'na g', text: DASH }), el('td', { class: 'na', text: DASH }), el('td', { class: 'na', text: DASH })];
  return [
    el('td', { class: 'num g', text: whole ? formatNumber(cell.total, 0) : cell.total }),
    el('td', { class: 'num', text: days(cell.t) }),
    el('td', { class: 'num', text: percent(cell.c) }),
  ];
}

/**
 * @param {object} options
 * @param {string} options.id
 * @param {string} options.title
 * @param {string} options.hint
 * @param {any} options.matrix headers, rows y totals de la API.
 * @param {string} options.managerUrl
 * @param {boolean} options.byMonth Encabezados con scope y ayudas (mes) o simples (trimestre).
 */
export function renderHistory({ id, title, hint, matrix, managerUrl, byMonth }) {
  const whole = !byMonth;
  const link = (/** @type {any} */ row) => el('a', { href: managerUrl.replace('slug-placeholder', encodeURIComponent(row.slug)), text: row.name });
  const first = byMonth
    ? el('tr', {}, el('th', { scope: 'col', rowspan: 2, text: 'DM' }), ...matrix.headers.map((/** @type {string} */ label) => el('th', { scope: 'colgroup', class: 'q', colspan: 3, text: label })))
    : el('tr', {}, el('th', { text: 'DM' }), ...matrix.headers.map((/** @type {string} */ label) => el('th', { class: 'q', colspan: 3, text: label })));
  const second = byMonth
    ? el(
        'tr',
        {},
        ...matrix.headers.flatMap(() => [
          el('th', { scope: 'col', text: 'TP' }),
          el('th', { scope: 'col', title: 'Desviación en días', text: 'T' }),
          el('th', { scope: 'col', title: 'Consumo de horas sobre presupuesto', text: 'C' }),
        ]),
      )
    : el('tr', {}, el('th'), ...matrix.headers.flatMap(() => ['TP', 'T', 'C'].map((text) => el('th', { text }))));
  const body = matrix.rows.map((/** @type {any} */ row) =>
    byMonth
      ? el('tr', {}, el('th', { scope: 'row' }, link(row)), ...row.cells.flatMap((/** @type {any} */ c) => cells(c)))
      : el('tr', {}, el('td', {}, el('b', {}, link(row))), ...row.cells.flatMap((/** @type {any} */ c) => cells(c, whole))),
  );
  const foot = el(
    'tr',
    {},
    byMonth ? el('th', { scope: 'row', text: 'Total' }) : el('td', { text: 'Total' }),
    ...matrix.totals.flatMap((/** @type {any} */ c) => cells(c, whole)),
  );
  return el(
    'section',
    { class: 'card', style: { marginBottom: '14px' } },
    el('h2', { text: title }),
    el('div', { class: 'hs', text: hint }),
    el('div', { class: 'table-scroll' }, el('table', { class: 'kpi-history-table', id }, el('thead', {}, first, second), el('tbody', {}, ...body), el('tfoot', {}, foot))),
  );
}
