// @ts-check
// Facturacion, margen y cobranza de la cuenta. Pide sus cifras por separado:
// quien no tiene permiso de costos no ve la seccion.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { formatMoney, formatNumber } from '#app/lib/format.js';

/**
 * @param {string} title
 * @param {string} footnote
 */
function card(title, footnote) {
  const value = el('strong', { text: '—' });
  const note = el('p', { class: 'note', text: 'Consultando...' });
  return { value, note, node: el('div', { class: 'card finance-card' }, el('b', { text: title }), value, note, el('small', { text: footnote })) };
}

/**
 * @param {HTMLElement} container
 * @param {string} client
 * @param {Record<string, string>} period Parametros del periodo de la URL.
 */
export async function renderFinance(container, client, period) {
  const revenue = card('Facturación', 'DataRevenue · facturado y cobrado; validación pendiente con Florencia');
  const margin = card('Margen bruto', '(Ingresos − costos) ÷ ingresos');
  const collections = card('Cobranza', 'Collected ÷ (Invoiced + Collected) · incluye factoring');
  const section = el(
    'section',
    { class: 'finance', 'aria-label': 'Finanzas de la cuenta' },
    el('span', { class: 'badge yellow', text: 'Datos 2026' }),
    el('div', { class: 'finance-cards' }, revenue.node, margin.node, collections.node),
  );
  try {
    const { data } = await apiGet('screens/cuenta/finanzas/', { nombre: client, ...period });
    const account = data.account;
    if (!account) {
      for (const item of [revenue, margin, collections]) {
        item.value.textContent = 'Sin datos';
        item.note.textContent = 'Sin registros de esta cuenta en DataRevenue 2026';
      }
    } else {
      revenue.value.textContent = formatMoney(account.revenue);
      revenue.note.textContent = `${account.projects} proyectos · 2026`;
      margin.value.textContent = account.margin == null ? 'Sin dato' : `${formatNumber(account.margin)}%${account.pending ? '*' : ''}`;
      margin.note.textContent = `${account.pending ? `* Provisional · ${account.pending} pendientes · ` : ''}Costos: ${formatMoney(account.cost)}`;
      collections.value.textContent = account.collections_percent == null ? 'Sin dato' : `${formatNumber(account.collections_percent)}%`;
      collections.note.textContent = `Cobrado: ${formatMoney(account.collected)} de ${formatMoney(account.invoiced)}`;
    }
  } catch (error) {
    // Sin permiso de costos la seccion no existe; cualquier otro fallo se dice.
    if (error instanceof Error && 'code' in error && error.code === 'forbidden') return;
    for (const item of [revenue, margin, collections]) item.note.textContent = 'No se pudo cargar la información';
  }
  container.append(section);
}
