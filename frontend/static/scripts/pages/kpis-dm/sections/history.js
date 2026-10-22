// @ts-check
// Historico por mes y por trimestre: TP, T y C de cada Delivery Manager.
import { withReturn } from '#app/data/navigation.js';
import { el } from '#app/lib/dom.js';
import { known } from './summary.js';

/** @param {any} cell @param {boolean} rounded */
function cells(cell, rounded) {
  if (!cell) return [el('td', { class: 'na g', text: '—' }), el('td', { class: 'na', text: '—' }), el('td', { class: 'na', text: '—' })];
  return [el('td', { class: 'n g', text: String(rounded ? Math.round(cell.total) : cell.total) }), el('td', { class: 'n', text: known(cell.t, ' d') }), el('td', { class: 'n', text: known(cell.c, '%') })];
}

/**
 * @param {HTMLElement} container
 * @param {object} options
 * @param {string} options.id
 * @param {string} options.title
 * @param {string} options.hint
 * @param {any} options.matrix
 * @param {string} options.dmUrl
 * @param {boolean} options.rounded TP trimestral es un promedio y se muestra redondeado.
 * @param {boolean} options.monthly El mensual lleva el DM como encabezado de fila.
 */
export function renderHistory(container, { id, title, hint, matrix, dmUrl, rounded, monthly }) {
  const sub = matrix.headers.flatMap(() => ['TP', 'T', 'C']);
  const head = monthly
    ? [
        el('tr', {}, el('th', { scope: 'col', rowspan: 2, text: 'DM' }), ...matrix.headers.map((/** @type {string} */ h) => el('th', { scope: 'colgroup', class: 'q', colspan: 3, text: h }))),
        el('tr', {}, ...sub.map((label) => el('th', { scope: 'col', text: label }))),
      ]
    : [
        el('tr', {}, el('th', { text: 'DM' }), ...matrix.headers.map((/** @type {string} */ h) => el('th', { class: 'q', colspan: 3, text: h }))),
        el('tr', {}, el('th'), ...sub.map((label) => el('th', { text: label }))),
      ];
  /** @param {any} row */
  const name = (row) => {
    const link = el('a', { href: withReturn(dmUrl.replace('DM_SLUG', row.slug)), text: row.name });
    return monthly ? el('th', { scope: 'row' }, link) : el('td', {}, el('b', {}, link));
  };
  const total = monthly ? el('th', { scope: 'row', text: 'Total' }) : el('td', { text: 'Total' });
  container.append(
    el(
      'section',
      { class: 'card' },
      el('h2', { text: title }),
      el('div', { class: 'hs', text: hint }),
      el(
        'div',
        { class: 'table-scroll' },
        el(
          'table',
          { class: 'kpi-history-table', id },
          el('thead', {}, ...head),
          el('tbody', {}, ...matrix.rows.map((/** @type {any} */ row) => el('tr', {}, name(row), ...row.cells.flatMap((/** @type {any} */ c) => cells(c, rounded))))),
          el('tfoot', {}, el('tr', {}, total, ...matrix.totals.flatMap((/** @type {any} */ c) => cells(c, rounded)))),
        ),
      ),
    ),
  );
}
