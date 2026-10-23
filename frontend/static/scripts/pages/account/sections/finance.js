// @ts-check
// Datos 2026 de la cuenta: facturacion, margen bruto y cobranza.
import { apiGet } from '#app/data/api-client.js';
import { el, svg } from '#app/lib/dom.js';
import { formatCompact, formatNumber } from '#app/lib/format.js';

const IDS = ['revenue', 'margin', 'collections'];

/** @param {string} id @param {string} text */
const put = (id, text) => {
  /** @type {HTMLElement} */ (document.getElementById(id)).textContent = text;
};

/**
 * @param {string} title
 * @param {string} key
 * @param {[string, Record<string, string | number>][]} shapes
 * @param {string} footnote
 * @param {Node[]} [extra] Contenido a la derecha del titulo.
 */
function card(title, key, shapes, footnote, extra = []) {
  return el(
    'div',
    { class: 'financial-card' },
    el(
      'header',
      {},
      el('span', { class: 'financial-icon' }, svg('svg', { viewBox: '0 0 24 24' }, ...shapes.map(([tag, attrs]) => svg(tag, attrs)))),
      el('b', { text: title }),
      ...extra,
    ),
    el('strong', { id: `account-finance-${key}`, text: '—' }),
    el('p', { id: `account-finance-${key}-note`, text: 'Consultando...' }),
    el('small', { text: footnote }),
  );
}

/** @param {string} costsUrl Detalle de costos de la cuenta. */
export function renderFinance(costsUrl) {
  const more = el('a', { href: costsUrl, style: { marginLeft: 'auto', fontSize: '11px', color: '#6126ef' }, text: 'Ver más →' });
  return el(
    'section',
    { class: 'financial-preview', 'aria-label': 'Finanzas de la cuenta 2026' },
    el('div', { class: 'preview-label', text: 'Datos 2026' }),
    el(
      'div',
      { class: 'financial-cards' },
      card('Facturación', 'revenue', [['path', { d: 'M5 19v-5M10 19V9M15 19V5M20 19V2' }]], 'DataRevenue · facturado y cobrado; validación pendiente con Florencia'),
      card('Margen bruto', 'margin', [['path', { d: 'm6 18 12-12' }], ['circle', { cx: 7, cy: 7, r: 3 }], ['circle', { cx: 17, cy: 17, r: 3 }]], '(Ingresos − costos) ÷ ingresos', [more]),
      card('Cobranza', 'collections', [['ellipse', { cx: 12, cy: 5, rx: 7, ry: 3 }], ['path', { d: 'M5 5v14c0 4 14 4 14 0V5M5 10c0 4 14 4 14 0M5 15c0 4 14 4 14 0' }]], 'Collected ÷ (Invoiced + Collected) · incluye factoring'),
    ),
  );
}

/** @param {Record<string, string>} params nombre y, si lo hay, el periodo. */
export async function loadFinance(params) {
  try {
    const { data } = await apiGet('screens/cuenta/finanzas/', params);
    const account = data.account;
    if (!account) {
      for (const id of IDS) {
        put(`account-finance-${id}`, 'Sin datos');
        put(`account-finance-${id}-note`, 'Sin registros de esta cuenta en DataRevenue 2026');
      }
      return;
    }
    put('account-finance-revenue', formatCompact(account.revenue));
    put('account-finance-revenue-note', `${account.projects} proyectos · 2026`);
    put('account-finance-margin', account.margin === null ? 'Sin dato' : `${formatNumber(account.margin, 2)}%${account.pending ? '*' : ''}`);
    put('account-finance-margin-note', `${account.pending ? `* Provisional · ${account.pending} pendientes · ` : ''}Costos: ${formatCompact(account.cost)}`);
    put('account-finance-collections', account.collections_percent === null ? 'Sin dato' : `${formatNumber(account.collections_percent, 2)}%`);
    put('account-finance-collections-note', `Cobrado: ${formatCompact(account.collected)} de ${formatCompact(account.invoiced)}`);
  } catch (_) {
    for (const id of IDS) put(`account-finance-${id}-note`, 'No se pudo cargar la informacion');
  }
}
