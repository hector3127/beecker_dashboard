// @ts-check
// Ventana con la lista de lo que falta revisar (costos, presupuestos...).
import { el, svg } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';

/** @type {HTMLDialogElement | null} */
let current = null;

/**
 * @param {object} options
 * @param {string} options.title
 * @param {string} options.description
 * @param {string[]} options.columns
 * @param {string[][]} options.rows
 * @param {HTMLElement} options.trigger Recibe el foco al cerrar.
 */
export function showPendingDialog({ title, description, columns, rows, trigger }) {
  if (current) current.close();
  const close = () => dialog.close();
  const dismiss = el(
    'button',
    { type: 'button', class: 'pending-dialog-dismiss', 'aria-label': 'Cerrar pendientes', autofocus: true, onclick: close },
    svg('svg', { viewBox: '0 0 24 24', width: 20, height: 20, fill: 'none', stroke: 'currentColor', 'stroke-width': 2, 'aria-hidden': 'true' }, svg('path', { d: 'm6 6 12 12M18 6 6 18' })),
  );
  const body = rows.map((row) =>
    el(
      'tr',
      {},
      ...row.map((cell, i) =>
        i === 0
          ? el('th', { scope: 'row', text: cell })
          : el('td', { 'data-label': columns[i], class: columns.length === 3 && i === 1 ? 'pending-dialog-amount' : null, text: cell }),
      ),
    ),
  );
  const dialog = /** @type {HTMLDialogElement} */ (
    el(
      'dialog',
      { class: 'portal-pending-dialog', 'aria-labelledby': 'pending-dialog-title', 'aria-describedby': 'pending-dialog-description' },
      el(
        'div',
        { class: 'pending-dialog-frame' },
        el(
          'header',
          { class: 'pending-dialog-header' },
          el(
            'div',
            {},
            el('span', { class: 'pending-dialog-count', text: `${formatNumber(rows.length, 0)} ${rows.length === 1 ? 'proyecto por revisar' : 'proyectos por revisar'}` }),
            el('h2', { id: 'pending-dialog-title', text: title }),
          ),
          dismiss,
        ),
        el('p', { id: 'pending-dialog-description', class: 'pending-dialog-description', text: description }),
        el(
          'div',
          { class: 'pending-dialog-scroll', tabindex: 0, role: 'region', 'aria-label': 'Lista de proyectos pendientes' },
          el(
            'table',
            {},
            el('caption', { class: 'portal-sr-only', text: title }),
            el('thead', {}, el('tr', {}, ...columns.map((c) => el('th', { scope: 'col', text: c })))),
            el('tbody', {}, ...body),
          ),
        ),
        el(
          'footer',
          { class: 'pending-dialog-footer' },
          el('span', { text: 'Presiona Esc para cerrar' }),
          el('button', { type: 'button', class: 'portal-button portal-button-primary close-blockers', text: 'Cerrar', onclick: close }),
        ),
      ),
    )
  );
  dialog.addEventListener(
    'close',
    () => {
      dialog.remove();
      if (current === dialog) {
        current = null;
        document.documentElement.classList.remove('portal-modal-open');
        trigger.focus({ preventScroll: true });
      }
    },
    { once: true },
  );
  document.body.appendChild(dialog);
  current = dialog;
  document.documentElement.classList.add('portal-modal-open');
  dialog.showModal();
}
