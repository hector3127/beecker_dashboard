// @ts-check
// Facturabilidad: cifra del mes y grafica mensual; el calculo es del servidor.
import { el } from '#app/lib/dom.js';
import { createBillingChart } from '#app/ui/billing-chart.js';

const RESTRICTED = 'Cifras del equipo completo: no disponibles con tu acceso.';

/**
 * @param {HTMLElement} root
 * @param {{restricted: boolean, data: any | null, failed: boolean}} state
 */
export function renderBilling(root, { restricted, data, failed }) {
  if (restricted) {
    root.replaceChildren(el('p', { class: 'ops-muted', text: RESTRICTED }));
  } else if (data) {
    root.replaceChildren(createBillingChart(data));
  } else if (failed) {
    root.replaceChildren(el('p', { class: 'ops-muted', text: 'No se pudo cargar facturabilidad. Consulta el detalle o vuelve a actualizar.' }));
  } else {
    root.replaceChildren(el('p', { class: 'ops-muted', text: 'Cargando facturabilidad...' }));
  }
}
