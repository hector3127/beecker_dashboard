// @ts-check
// Tabla de oportunidades con sus IDs ligados, busqueda y detalle plegable.
import { el } from '#app/lib/dom.js';
import { formatMoney, plain } from '#app/lib/format.js';
import { marginIcon } from './summary.js';

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
      el('td', {}, `${formatMoney(p.cost)}${p.partial && p.cost !== null ? '*' : ''}`,
        ...(p.shared ? [el('small', { class: 'margin-data-status', text: 'Total del ID compartido' })] : [])),
      el('td', { text: formatMoney(p.period_revenue) }),
      el('td', { class: tone(p.gross_profit),
        text: `${margin}${p.partial && p.gross_profit !== null ? '*' : ''}` }),
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
      { colspan: 10 },
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
      el('span', { class: 'opportunity-document-icon' }, marginIcon('document')),
      el('strong', { text: o.name }),
      el('small', { text: o.services.join(', ') }),
    ),
    number(
      o.bookings !== null ? formatMoney(o.bookings) : PENDING,
      el('small', { text: `Revenue del periodo: ${formatMoney(o.period_revenue)}` }),
    ),
    number(formatMoney(o.operated_revenue)),
    number(formatMoney(o.invoiced)),
    number(formatMoney(o.collected)),
    number(costCell(o), ...(o.allocation_pending
      ? [el('small', { class: 'margin-data-status', text: 'Referencia compartida' })] : [])),
    el('td', {}, twoDecimals(o.sold_margin), ...(o.sold_margin > 100
      ? [el('small', { class: 'margin-data-status margin-source-warning', text: 'Validar dato de origen (>100%)' })] : [])),
    el('td', { text: `${twoDecimals(o.actual_margin)}${o.actual_margin !== null ? star(o.partial) : ''}` }),
    el(
      'td',
      { class: `deviation-cell ${tone(o.deviation_pp)}` },
      el('span', { class: 'deviation-value', text: `${twoDecimals(o.deviation_pp, ' pp')}${o.deviation_pp !== null ? star(o.partial) : ''}` }),
    ),
    el('td', { class: 'opportunity-detail-action' }, toggle),
  );
  return { main, panel: panel(o, index), toggle, account: o.account };
}

/**
 * @param {any[]} opportunities
 * @param {any[]} [accounts]
 * @returns {HTMLElement}
 */
export function renderResults(opportunities, accounts = []) {
  const heads = ['Cuenta / oportunidad', 'Bookings', 'Revenue operado', 'Facturado', 'Cobrado', 'Costos', 'Margen vendido', 'Margen real', 'Desviación (pp)', 'Detalle'];
  const rows = opportunities.map((o, i) => row(o, i + 1));
  // Los totales vienen del mismo corte del servidor, con costos deduplicados.
  const groups = new Map();
  for (const r of rows) {
    if (!groups.has(r.account)) groups.set(r.account, { account: r.account, rows: [], open: false });
    groups.get(r.account).rows.push(r);
  }
  const body = [];
  for (const [index, group] of [...groups.values()].entries()) {
    group.button = el('button', {
      type: 'button', class: 'account-group-toggle', 'aria-expanded': 'false',
      'aria-controls': `account-opportunities-${index}`,
    }, el('span', { class: 'account-chevron', 'aria-hidden': 'true', text: '›' }),
    el('span', { class: 'account-group-icon' }, marginIcon('account')),
    el('span', {}, el('strong', { text: group.account || 'Sin cuenta' }),
      el('small', { class: 'account-group-count' })));
    group.action = el('button', { type: 'button', class: 'account-group-action',
      'aria-expanded': 'false', 'aria-controls': `account-opportunities-${index}`,
      text: 'Ver oportunidades' });
    const totals = accounts.find(a => a.account === group.account);
    const moneyCell = (value, partial = false) => el('td', { class: 'number' },
      `${formatMoney(value)}${value !== null && partial ? '*' : ''}`);
    const percentCell = (value, partial = false) => el('td', { class: 'number' },
      `${twoDecimals(value)}${value !== null && partial ? '*' : ''}`);
    const cells = totals ? [
      moneyCell(totals.bookings, totals.bookings_partial), moneyCell(totals.operated_revenue),
      moneyCell(totals.invoiced), moneyCell(totals.collected),
      moneyCell(totals.cost, totals.cost_partial),
      percentCell(totals.sold_margin, totals.sold_partial),
      percentCell(totals.actual_margin, totals.cost_partial),
      el('td', { class: `deviation-cell ${tone(totals.deviation_pp)}` },
        el('span', { class: 'deviation-value', text:
          `${twoDecimals(totals.deviation_pp, ' pp')}${totals.deviation_pp !== null && totals.partial ? '*' : ''}` })),
    ] : Array.from({ length: 8 }, () => el('td', { text: PENDING }));
    if (totals?.sold_source_warning) cells[5].append(el('small', {
      class: 'margin-data-status margin-source-warning', text: 'Validar dato de origen',
    }));
    group.header = el('tr', { class: 'account-group-row',
      title: 'Totales de la cuenta para el rango seleccionado' },
      el('td', {}, group.button), ...cells, el('td', {}, group.action));
    group.section = el('tbody', { id: `account-opportunities-${index}`, class: 'account-opportunities' },
      ...group.rows.flatMap(r => [r.main, r.panel]));
    body.push(el('tbody', { class: 'account-group-heading' }, group.header), group.section);
  }
  if (!rows.length) body.push(el('tbody', {}, el('tr', {}, el('td', { colspan: 10,
    text: 'No hay oportunidades en el periodo con el alcance seleccionado.' }))));
  const search = /** @type {HTMLInputElement} */ (
    el('input', { id: 'opportunity-search', type: 'search', 'aria-label': 'Buscar cuenta, oportunidad o proyecto', placeholder: 'Buscar cuenta, oportunidad o Project ID…' })
  );
  const count = el('small', { id: 'opportunity-count' });

  function draw() {
    let shown = 0;
    for (const group of groups.values()) {
      let matches = 0;
      for (const r of group.rows) {
        const match = plain(r.main.dataset.opportunity).includes(plain(search.value));
        if (match) { shown += 1; matches += 1; }
        r.main.hidden = !match;
        r.panel.hidden = !match || r.toggle.getAttribute('aria-expanded') !== 'true';
      }
      group.header.hidden = matches === 0;
      group.section.hidden = !group.open || matches === 0;
      group.button.setAttribute('aria-expanded', String(group.open));
      group.action.setAttribute('aria-expanded', String(group.open));
      group.action.textContent = group.open ? 'Ocultar oportunidades' : 'Ver oportunidades';
      group.button.querySelector('.account-group-count').textContent = `${matches} ${matches === 1 ? 'oportunidad' : 'oportunidades'}`;
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
  for (const group of groups.values()) {
    const toggleGroup = () => { group.open = !group.open; draw(); };
    group.button.addEventListener('click', toggleGroup);
    group.action.addEventListener('click', toggleGroup);
  }
  search.addEventListener('input', () => {
    if (search.value) for (const group of groups.values()) {
      group.open = true;
      group.button.setAttribute('aria-expanded', 'true');
    }
    draw();
  });

  const card = el(
    'div',
    { class: 'opportunity-card opportunity-results' },
    el('div', { class: 'opportunity-search-field' }, marginIcon('search'), search),
    count,
    el('div', { class: 'scroll' }, el('table', {}, el('thead', {}, el('tr', {}, ...heads.map((h) => el('th', { text: h })))), ...body)),
  );
  draw();
  return card;
}
