// @ts-check
// Inversion: el mes elegido recarga la pagina y las barras toman su ancho.
import { watchLoadingMessages } from '#app/ui/portal-loading.js';

watchLoadingMessages();
document.querySelectorAll('[data-width]').forEach((node) => {
  /** @type {HTMLElement} */ (node).style.width = `${/** @type {HTMLElement} */ (node).dataset.width}%`;
});
document.getElementById('mes')?.addEventListener('change', (event) => {
  /** @type {HTMLFormElement} */ (/** @type {HTMLInputElement} */ (event.target).form).submit();
});
