// @ts-check
// Ventana de detalle con <dialog>: foco atrapado y Escape los pone el navegador.
// Abre vacia; quien la llama llena el cuerpo con nodos.
import { el } from '#app/lib/dom.js';

/** @type {HTMLDialogElement | null} */
let dialog = null;

/**
 * @param {string} title
 * @param {{wide?: boolean}} [options]
 * @returns {HTMLElement} El cuerpo, para que quien llama lo llene.
 */
export function openDetail(title, options = {}) {
  if (!dialog) {
    dialog = /** @type {HTMLDialogElement} */ (el('dialog', { class: 'detail-dialog', 'aria-labelledby': 'detail-dialog-title' }));
    document.body.append(dialog);
  }
  const body = el('div', { class: 'detail-body' });
  const close = el('button', { type: 'button', class: 'btn btn-ghost detail-close', 'aria-label': 'Cerrar', text: '×', onclick: () => dialog?.close() });
  dialog.classList.toggle('wide', Boolean(options.wide));
  dialog.replaceChildren(el('header', {}, el('h2', { id: 'detail-dialog-title', text: title }), close), body);
  if (!dialog.open) dialog.showModal();
  return body;
}
