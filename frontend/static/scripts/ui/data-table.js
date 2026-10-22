// @ts-check
// Tabla con el modelo compartido: caption accesible, encabezados con scope y
// una fila de aviso cuando no hay datos. No conoce de donde vienen las filas.
import { el } from '#app/lib/dom.js';

/**
 * @typedef {object} Column
 * @property {string} header
 * @property {boolean} [numeric] Alinea a la derecha.
 * @property {(row: any) => Node | string | null} cell
 * @property {(row: any) => string} [cellClass] Clase extra segun la fila.
 */

/**
 * @param {object} options
 * @param {string} options.id
 * @param {string} [options.className]
 * @param {string} options.caption Texto para lectores de pantalla.
 * @param {Column[]} options.columns
 * @param {any[]} options.rows
 * @param {string} options.emptyText
 * @returns {HTMLTableElement}
 */
export function buildTable({ id, className = '', caption, columns, rows, emptyText }) {
  const head = el(
    'tr',
    {},
    ...columns.map((column) => el('th', { scope: 'col', class: column.numeric ? 'n' : '', text: column.header })),
  );
  const body = rows.length
    ? rows.map((row) =>
        el(
          'tr',
          {},
          ...columns.map((column) => {
            const classes = [column.numeric ? 'n' : '', column.cellClass?.(row) || ''].filter(Boolean).join(' ');
            return el('td', { class: classes }, column.cell(row) ?? '');
          }),
        ),
      )
    : [el('tr', {}, el('td', { colspan: columns.length, text: emptyText }))];
  return /** @type {HTMLTableElement} */ (
    el(
      'table',
      { id, class: className },
      el('caption', { class: 'sr-only', text: caption }),
      el('thead', {}, head),
      el('tbody', {}, ...body),
    )
  );
}
