// @ts-check
// Tabla de oportunidades con sus IDs ligados, busqueda y detalle plegable.
import { el } from '#app/lib/dom.js';
import { formatMoney, plain } from '#app/lib/format.js';

const PENDING = 'Pendiente';
/** @param {number | null | undefined} value @param {string} [unit] */
const twoDecimals = (value, unit = '%') =>
  value === null || value === undefined ? PENDING : `${value.toFixed(2)}${unit}`;
/** Clase segun el signo: negativo malo, positivo bueno. @param {number | null} value */
const tone = (value) => (value !== null && value < 0 ? 'bad' : value !== null && value > 0 ? 'good' : '');
/** @param {boolean} partial */
const star = (partial) => (partial ? '*' : '');

/** @param {any} o */
function costCell(o) {
  if (o.cost !== null) return `${formatMoney(o.cost)}${star(o.partial)}`;
  return o.allocation_pending ? 'Sin costo consultado' : PENDING;
}

/** @param {any} p @param {string} account */
function linkedProject(p, account) {
  let margin = PENDING;
  if (p.margin !== null) margin = twoDecimals(p.margin);
  else if (p.gross_profit !== null) margin = formatMoney(p.gross_profit);
  else if (p.shared) margin = 'Sin costo consultado';
  const issues = p.issues.length ? p.issues.map((/** @type {string} */ i) => el('small', { text: i })) : ['Costo completo'];
  return [
    el(
      'tr',
      {},
      el('td', {}, el('strong', { text: p.id })),
      el('td', { text: p.hours === null ? PENDING : String(p.hours) }),
      el('td', { text: `${formatMoney(p.cost)}${p.partial && p.cost !== null ? '*' : ''}` }),
      el('td', { text: formatMoney(p.period_revenue) }),
      el('td', { class: tone(p.gross_profit), text: `${margin}${p.partial && p.gross_profit !== null ? '*' : ''}` }),
      el('td', {}, ...issues),
    ),
    el(
      'tr',
      { class: 'people-panel-row' },
      el(
        'td',
        { colspan: 6 },
        el(
          'details',
          { class: 'opportunity-people', dataset: { project: p.id, account } },
          el('summary', { text: 'Ver personas y tarifas' }),
          el('div', { class: 'opportunity-people-content', text: 'Abre para consultar el desglose.' }),
        ),
      ),
    ),
  ];
}

/** @param {any} o @param {number} index */
function panel(o, index) {
  const title = el('h3', {}, el('span', { class: 'link-symbol', 'aria-hidden': 'true', text: '↗' }), `${o.name} · IDs ligados${o.partial ? ' · Parcial*' : ''}`);
  const heads = ['Project ID', 'Horas', 'Costo', 'Revenue del periodo', 'Margen bruto (% / importe)', 'Estado / error'];
  return el(
    'tr',
    { id: `opportunity-panel-${index}`, class: 'opportunity-panel-row', hidden: true },
    el(
      'td',
      { colspan: 11 },
      el(
        'div',
        { class: 'opportunity-panel' },
        title,
        ...o.issues.map((/** @type {string} */ issue) => el('small', { text: issue })),
        el(
          'table',
          {},
          el('thead', {}, el('tr', {}, ...heads.map((h) => el('th', { text: h })))),
          el('tbody', {}, ...o.projects.flatMap((/** @type {any} */ p) => linkedProject(p, o.account))),
        ),
      ),
    ),
  );
}

/** @param {any} o @param {number} index */
function row(o, index) {
  const toggle = el('button', {
    type: 'button',
    'data-opportunity-toggle': `opportunity-panel-${index}`,
    'aria-controls': `opportunity-panel-${index}`,
    'aria-expanded': 'false',
    text: `Ver IDs ligados (${o.projects.length})`,
  });
  const number = (/** @type {Node | string} */ ...content) => el('td', { class: 'number' }, ...content);
  const main = el(
    'tr',
    { 'data-opportunity': `${o.account} ${o.name} ${o.ids.join(' ')}` },
    el(
      'td',
      { class: 'opportunity-name' },
      el('span', { class: 'row-arrow', 'aria-hidden': 'true', text: '›' }),
      el('strong', { text: o.account }),
      el('small', { text: o.name }),
      el('small', { text: o.services.join(', ') }),
    ),
    number(
      o.bookings !== null ? formatMoney(o.bookings) : PENDING,
      el('small', { text: `Revenue del periodo: ${formatMoney(o.period_revenue)}` }),
    ),
    number(formatMoney(o.operated_revenue), el('small', { text: 'Fecha de servicio: G · por validar' })),
    number(formatMoney(o.invoiced)),
    number(formatMoney(o.collected)),
    number(costCell(o)),
    el('td', { class: 'sold-rate-pending' }, el('strong', { text: PENDING }), el('small', { text: 'Por validar con Florencia' })),
    el('td', { text: twoDecimals(o.sold_margin) }),
    el('td', { text: `${twoDecimals(o.actual_margin)}${o.actual_margin !== null ? star(o.partial) : ''}` }),
    el(
      'td',
      { class: `deviation-cell ${tone(o.deviation_pp)}` },
      el('span', { class: 'deviation-value', text: `${twoDecimals(o.deviation_pp, ' pp')}${o.deviation_pp !== null ? star(o.partial) : ''}` }),
    ),
    el('td', {}, toggle),
  );
  return { main, panel: panel(o, index), toggle };
}

/**
 * @param {any[]} opportunities
 * @returns {HTMLElement}
 */
export function renderResults(opportunities) {
  const heads = ['Cuenta / oportunidad', 'Bookings', 'Revenue operado', 'Facturado', 'Cobrado', 'Costos', 'Tarifa de costo vendida', 'Margen vendido', 'Margen real', 'Desviación (pp)', 'Detalle'];
  const rows = opportunities.map((o, i) => row(o, i + 1));
  const body = rows.length
    ? rows.flatMap((r) => [r.main, r.panel])
    : [el('tr', {}, el('td', { colspan: 11, text: 'No hay oportunidades en el periodo con el alcance seleccionado.' }))];
  const search = /** @type {HTMLInputElement} */ (
    el('input', { id: 'opportunity-search', type: 'search', 'aria-label': 'Buscar cuenta, oportunidad o proyecto', placeholder: 'Buscar cuenta, oportunidad o Project ID…' })
  );
  const count = el('small', { id: 'opportunity-count' });

  function draw() {
    let shown = 0;
    for (const r of rows) {
      r.main.hidden = !plain(/** @type {string} */ (r.main.dataset.opportunity)).includes(plain(search.value));
      if (!r.main.hidden) shown += 1;
      r.panel.hidden = r.main.hidden || r.toggle.getAttribute('aria-expanded') !== 'true';
    }
    count.textContent = `${shown} de ${rows.length} oportunidades`;
  }
  for (const r of rows) {
    r.toggle.addEventListener('click', () => {
      const open = r.toggle.getAttribute('aria-expanded') === 'true';
      r.toggle.setAttribute('aria-expanded', String(!open));
      r.panel.hidden = open;
      r.main.classList.toggle('is-expanded', !open);
      r.toggle.textContent = open ? 'Ver IDs ligados' : 'Ocultar IDs ligados';
    });
  }
  search.addEventListener('input', draw);

  const card = el(
    'div',
    { class: 'opportunity-card opportunity-results' },
    search,
    count,
    el(
      'p',
      { class: 'opportunity-rate-note' },
      el('strong', { text: 'Tarifa de costo vendida:' }),
      ' fuente, unidad y asignación pendientes de validación con Florencia. No se sustituye por la tarifa interna de banda ni se deduce del revenue. Los márgenes actuales conservan su cálculo.',
    ),
    el('div', { class: 'scroll' }, el('table', {}, el('thead', {}, el('tr', {}, ...heads.map((h) => el('th', { text: h })))), el('tbody', {}, ...body))),
  );
  draw();
  return card;
}
