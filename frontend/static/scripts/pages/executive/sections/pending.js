// @ts-check
// Lista de proyectos con pendientes (costos u operaciones) en una ventana.
import { el } from '#app/lib/dom.js';
import { openDetail } from '#app/ui/detail-dialog.js';

/**
 * @param {object} options
 * @param {string} options.title
 * @param {string} options.description
 * @param {string[]} options.columns
 * @param {string[][]} options.rows La primera columna es el proyecto.
 */
export function openPending({ title, description, columns, rows }) {
  const body = openDetail(title);
  body.append(
    el('p', { class: 'note', text: `${rows.length} ${rows.length === 1 ? 'proyecto por revisar' : 'proyectos por revisar'}` }),
    el('p', { text: description }),
    el(
      'div',
      { class: 'detail-scroll' },
      el(
        'table',
        {},
        el('caption', { class: 'sr-only', text: title }),
        el('thead', {}, el('tr', {}, ...columns.map((c) => el('th', { scope: 'col', text: c })))),
        el('tbody', {}, ...rows.map((row) => el('tr', {}, ...row.map((cell, i) => (i === 0 ? el('th', { scope: 'row', text: cell }) : el('td', { text: cell })))))),
      ),
    ),
  );
}
