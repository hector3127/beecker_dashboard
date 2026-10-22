// @ts-check
// Tarjetas de Financiera, Operaciones y Comercial. Un dato que falta se dice
// «Pendiente» (o «No disponible»), nunca se muestra como cero.
import { el } from '#app/lib/dom.js';
import { formatCompact, formatNumber } from '#app/lib/format.js';
import { openPending } from './pending.js';

const PENDING = 'Pendiente';
const LIMITED = 'Cifra del portafolio completo; no disponible para tu alcance.';

/** @param {number | null | undefined} n */
const whole = (n) => (n == null ? PENDING : formatNumber(n, 0));
/** @param {number | null | undefined} n */
const pct = (n) => (n == null ? PENDING : `${whole(n)}%`);
/** @param {number | null | undefined} n */
const money = (n) => formatCompact(n);

/**
 * @param {string} label
 * @param {string} value
 * @param {string} [note]
 * @param {Node[]} [extra]
 */
function metric(label, value, note = '', extra = []) {
  return el('div', { class: 'metric-row' }, el('div', { class: 'metric-label', text: label }), el('div', { class: 'metric-value' }, el('b', { text: value }), ...(note ? [el('small', { text: note })] : []), ...extra));
}

/**
 * @param {string} title
 * @param {string} subtitle
 * @param {string} badge
 * @param {() => void} onInfo
 * @param {Node[]} body
 * @param {string} linkHref
 * @param {string} linkText
 */
function card(title, subtitle, badge, onInfo, body, linkHref, linkText) {
  return el(
    'section',
    { class: 'card exec-card', 'aria-label': title },
    el('header', {}, el('div', {}, el('h2', { text: title }), el('small', { text: subtitle })), el('span', { class: 'badge', text: badge }), el('button', { type: 'button', class: 'more', 'aria-label': `Ver fuentes y cálculo de ${title}`, text: 'ⓘ', onclick: onInfo })),
    ...body,
    el('a', { class: 'exec-link', href: linkHref, text: linkText }),
  );
}

/**
 * @param {any} data Datos de la API.
 * @param {any} meta
 * @param {{year: string, costsUrl: string, operationsUrl: string, commercialUrl: string, info: (group: string) => void}} options
 */
export function financeCard(data, meta, { year, costsUrl, info }) {
  const limited = meta.scope === 'limited';
  const finance = data.finance;
  if (!finance) {
    return card('Financiera', 'Facturación, margen y cobranza', year, () => info('Financiera'), [el('p', { class: 'note', text: limited ? LIMITED : 'El corte del periodo se está preparando.' })], costsUrl, 'Ver detalle financiero');
  }
  const revenue = finance.revenue || {};
  const costs = finance.costs || {};
  const hasInvoice = revenue.invoiced != null;
  const hasCosts = costs.cost != null && (costs.complete || (costs.projects || []).some((/** @type {any} */ p) => p.cost != null) || Number(costs.deduplicated_entries) > 0);
  const income = Number(revenue.invoiced);
  const marginValue = hasCosts && hasInvoice && income > 0 ? `${whole(((income - Number(costs.cost)) / income) * 100)}%${costs.complete ? '' : '*'}` : PENDING;
  const marginNote = hasCosts ? (costs.complete ? 'Costos completos · base de facturación pendiente de validar' : `* Parcial con costos disponibles: ${money(costs.cost)}.`) : 'Sin costos consultados para calcular el margen';
  const blockers = (costs.projects || []).filter((/** @type {any} */ p) => !p.complete);
  const blockersButton = blockers.length
    ? [
        el('button', {
          type: 'button',
          class: 'more',
          text: `${blockers.length} costos pendientes`,
          onclick: () =>
            openPending({
              title: 'Pendientes de costos',
              description: 'El margen es parcial mientras falten vínculos, fechas o tarifas. Los costos disponibles ya están incluidos en el cálculo.',
              columns: ['Proyecto', 'Costo disponible', 'Qué falta revisar'],
              rows: blockers.map((/** @type {any} */ p) => [p.id, money(p.cost), p.error || `Falta banda o tarifa${p.missing_people?.length ? `: ${p.missing_people.join(', ')}` : ''}`]),
            }),
        }),
      ]
    : [];
  return card(
    'Financiera',
    'Facturación, margen y cobranza',
    year,
    () => info('Financiera'),
    [metric('Facturación del periodo', money(revenue.invoiced)), metric('Margen bruto', marginValue, marginNote, blockersButton), metric('Cobranza', pct(revenue.collections_percent))],
    costsUrl,
    'Ver detalle financiero',
  );
}

/** @param {any} data @param {any} meta @param {{operationsUrl: string, info: (group: string) => void}} options */
export function operationsCard(data, meta, { operationsUrl, info }) {
  const limited = meta.scope === 'limited';
  const ops = data.operations;
  if (!ops) {
    return card('Operaciones', 'ETC, facturabilidad e inversión operativa', limited ? 'Alcance limitado' : 'Consultando', () => info('Operaciones'), [el('p', { class: 'note', text: limited ? LIMITED : 'El corte operativo se está preparando.' })], operationsUrl, 'Ver detalle de Operaciones');
  }
  const partial = ops.partial !== false;
  const star = partial ? '*' : '';
  const missing = (ops.missing_budget_ids || []).length;
  const noConsumption = (ops.pending_ids || []).length;
  const pendingIds = new Map(/** @type {[string, string[]][]} */ ([]));
  for (const id of ops.missing_budget_ids || []) pendingIds.set(id, ['Sin presupuesto']);
  for (const id of ops.pending_ids || []) pendingIds.set(id, [...(pendingIds.get(id) || []), 'Consumo pendiente']);
  const status = pendingIds.size
    ? el('button', {
        type: 'button',
        class: 'more',
        text: `${missing ? `${whole(missing)} sin presupuesto${noConsumption ? ` · ${whole(noConsumption)} sin consumo` : ''}` : `${whole(noConsumption)} sin consumo`}`,
        onclick: () =>
          openPending({
            title: 'Pendientes de Operaciones',
            description: 'Estos proyectos necesitan presupuesto o consumo para completar el corte operativo.',
            columns: ['Proyecto', 'Qué falta revisar'],
            rows: [...pendingIds].map(([id, reasons]) => [id, reasons.join(' · ')]),
          }),
      })
    : null;
  return card(
    'Operaciones',
    'ETC, facturabilidad e inversión operativa',
    partial ? 'Corte parcial' : 'Corte completo',
    () => info('Operaciones'),
    [
      ...(status ? [status] : []),
      metric('ETC · horas restantes', ops.etc != null ? `${whole(ops.etc)} h${star}` : PENDING, ops.fte != null ? `${formatNumber(ops.fte, 2)} FTE equivalentes` : 'FTE pendiente de corte completo'),
      metric('Avance en horas', ops.advance != null ? `${pct(ops.advance)}${star}` : PENDING, 'Consumo ÷ presupuesto'),
      metric('Facturabilidad global', ops.facturability == null ? PENDING : `${whole(ops.facturability)}%${ops.facturability_partial ? '*' : ''}`, ops.facturability_period ? `${ops.facturability_partial ? 'Parcial · ' : ''}${ops.facturability_period}` : ''),
      metric('Inversión operativa · horas', ops.investment_operational == null ? PENDING : `${whole(ops.investment_operational)} h`),
    ],
    operationsUrl,
    'Ver detalle de Operaciones',
  );
}

/** @param {any} data @param {any} meta @param {{commercialUrl: string, info: (group: string) => void}} options */
export function commercialCard(data, meta, { commercialUrl, info }) {
  const limited = meta.scope === 'limited';
  const c = data.commercial;
  if (!c) {
    return card('Comercial', 'Booking y capacidad comercial', limited ? 'Alcance limitado' : 'Consultando', () => info('Comercial'), [el('p', { class: 'note', text: limited ? LIMITED : 'El corte comercial se está preparando.' })], commercialUrl, 'Ver detalle de Comercial');
  }
  return card(
    'Comercial',
    'Booking y capacidad comercial',
    c.open_rule && c.delivery_rule ? 'Corte preparado' : 'Validaciones pendientes',
    () => info('Comercial'),
    [
      metric('Ventas cerradas', money(c.won), c.won_count == null ? 'Pendiente de corte' : `${whole(c.won_count)} ventas ganadas · booking`),
      metric('Trabajo por entregar', money(c.delivery), c.delivery_note || 'Pendiente de corte'),
      metric('Previas al cierre', money(c.open), c.open_note || 'Pendiente de corte'),
    ],
    commercialUrl,
    'Ver detalle de Comercial',
  );
}

