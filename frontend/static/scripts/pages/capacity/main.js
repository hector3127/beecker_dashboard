// @ts-check
// Los filtros y el CSV conservan el formulario GET y el calculo del servidor.
import { watchLoadingMessages } from '#app/ui/portal-loading.js';

watchLoadingMessages();
document.querySelectorAll('[data-auto-submit]').forEach((field) => {
  field.addEventListener('change', () => {
    /** @type {HTMLInputElement | HTMLSelectElement} */ (field).form?.submit();
  });
});
