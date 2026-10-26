// @ts-check
// Facturabilidad: cifra del mes y grafica mensual; el calculo es del servidor.
import { el } from '#app/lib/dom.js';
import { createBillingChart } from '#app/ui/billing-chart.js';

let range='9';
let selectedMonth=null;
const RESTRICTED = 'Cifras del equipo completo: no disponibles con tu acceso.';

/**
 * @param {HTMLElement} root
 * @param {{restricted: boolean, data: any | null, failed: boolean}} state
 */
export function renderBilling(root, { restricted, data, failed }) {
  const picker=document.getElementById('ops-billing-range');
  if(picker){picker.value=range;picker.disabled=restricted||!data;picker.onchange=()=>{range=picker.value;renderBilling(root,{restricted,data,failed});};}
  if (restricted) {
    root.replaceChildren(el('p', { class: 'ops-muted', text: RESTRICTED }));
  } else if (data) {
    const months=range==='all'?data.months:data.months.slice(-Number(range));
    root.replaceChildren(createBillingChart({...data,months},{selectedMonth,onSelect:month=>{selectedMonth=month;}}));
  } else if (failed) {
    root.replaceChildren(el('p', { class: 'ops-muted', text: 'No se pudo cargar facturabilidad. Consulta el detalle o vuelve a actualizar.' }));
  } else {
    root.replaceChildren(el('p', { class: 'ops-muted', text: 'Cargando facturabilidad...' }));
  }
}
