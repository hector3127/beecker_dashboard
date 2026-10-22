// @ts-check
// Los tres estados de una region: cargando, error con reintento y vacio.
// Reciben el contenedor y reemplazan su contenido; no saben de datos ni de URLs.
import { el } from '#app/lib/dom.js';

const GENERIC = 'No se pudo completar la consulta. Intenta de nuevo.';

/**
 * @param {HTMLElement} container
 * @param {string} [message]
 */
export function showLoading(container, message = 'Cargando…') {
  container.setAttribute('aria-busy', 'true');
  container.replaceChildren(el('div', { class: 'cargando', role: 'status', text: message }));
}

/**
 * @param {HTMLElement} container
 * @param {unknown} error Un ApiError o cualquier Error; solo se muestra su mensaje.
 * @param {{onRetry?: () => void}} [options]
 */
export function showError(container, error, options = {}) {
  container.removeAttribute('aria-busy');
  const message = error instanceof Error && error.message ? error.message : GENERIC;
  const box = el('div', { class: 'err', role: 'alert' }, message);
  if (options.onRetry) {
    box.append(el('button', { type: 'button', class: 'btn btn-ghost', onclick: options.onRetry, text: 'Reintentar' }));
  }
  container.replaceChildren(box);
}

/**
 * @param {HTMLElement} container
 * @param {string} message Texto honesto: que falta y por que.
 */
export function showEmpty(container, message) {
  container.removeAttribute('aria-busy');
  container.replaceChildren(el('div', { class: 'vacio', text: message }));
}

/** Quita el estado para que la pantalla pinte sus datos. @param {HTMLElement} container */
export function clearState(container) {
  container.removeAttribute('aria-busy');
  container.replaceChildren();
}
