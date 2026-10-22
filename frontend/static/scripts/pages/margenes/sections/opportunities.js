// @ts-check
// Tabla de oportunidades con sus IDs ligados y el buscador por cuenta, oportunidad o ID.
import { el } from '#app/lib/dom.js';
import { formatMoney, formatNumber, formatPercent, plain } from '#app/lib/format.js';
import { peopleDetails } from './people.js';

const PENDING = 'Pendiente';
const HEADERS = [
  'Cuenta / oportunidad',
  'Bookings',
  'Revenue operado',
  'Facturado',
  'Cobrado',
  'Costos',
  'Tarifa de costo vendida',
  'Margen vendido',
  'Margen real',
  'Desviación (pp)',
  'Detalle',
];
const PROJECT_HEADERS = ['Project ID', 'Horas', 'Costo', 'Revenue del periodo', 'Margen bruto (% / importe)', 'Estado / error'];
// El estado del contrato dice de donde sale el dato; la nota lo repite al lado.
const OPERATED_NOTE = /** @type {Record<string, string>} */ ({ assumed_service_date_g: 'Fecha de servicio: G · por validar' });
const RATE_NOTE = /** @type {Record<string, string>} */ ({ pending_validation: 'Por validar con Florencia' });

/** @param {number | null | undefined} value */
const tone = (value) => (value == null ? '' : value < 0 ? 'bad' : value > 0 ? 'good' : '');

/** @param {string[]} titles */
const headRow = (titles) => el('thead', {}, el('tr', {}, ...titles.map((title) => el('th', { scope: 'col', text: title }))));

/** @param {any} row */
function costCell(row) {
  if (row.cost != null) return formatMoney(row.cost) + (row.partial ? '*' : '');
  return row.allocation_pending ? 'Sin costo consultado' : PENDING;
}

/** @param {any} row */
function marginCell(row) {
  const text = formatPercent(row.actual_margin);
  return row.actual_margin != null && row.partial ? `${text}*` : text;
}

/** @param {any} project */
function grossCell(project) {
  const star = project.partial && project.gross_profit != null ? '*' : '';
  if (project.margin != null) return formatPercent(project.margin) + star;
  if (project.gross_profit != null) return formatMoney(project.gross_profit) + star;
  return project.shared ? 'Sin costo consultado' : PENDING;
}

/**
 * @param {any} row
 * @param {string} panelId
 * @param {() => Record<string, string>} periodParams
 */
function panel(row, panelId, periodParams) {
  const projects = row.projects.flatMap((/** @type {any} */ project) => [
    el(
      'tr',
      {},
      el('td', {}, el('strong', { text: project.id })),
      el('td', { text: project.hours == null ? PENDING : formatNumber(project.hours) }),
      el('td', { text: formatMoney(project.cost) + (project.partial && project.cost != null ? '*' : '') }),
      el('td', { text: formatMoney(project.period_revenue) }),
      el('td', { class: tone(project.gross_profit), text: grossCell(project) }),
      el(
        'td',
        {},
        ...(project.issues.length ? project.issues.map((/** @type {string} */ issue) => el('small', { text: issue })) : ['Costo completo']),
      ),
    ),
    el('tr', { class: 'mg-people-row' }, el('td', { colspan: PROJECT_HEADERS.length }, peopleDetails(project.id, row.account, periodParams))),
  ]);
  return el(
    'tr',
    { id: panelId, class: 'mg-panel-row', hidden: true },
    el(
      'td',
      { colspan: HEADERS.length },
      el(
        'div',
        { class: 'mg-panel' },
        el('h3', { text: `${row.name} · IDs ligados${row.partial ? ' · Parcial*' : ''}` }),
        ...row.issues.map((/** @type {string} */ issue) => el('small', { text: issue })),
        el('table', {}, headRow(PROJECT_HEADERS), el('tbody', {}, ...projects)),
      ),
    ),
  );
}

/** @param {any} row @param {HTMLElement} detailButton */
function summaryRow(row, detailButton) {
  const operatedNote = OPERATED_NOTE[row.operated_revenue_status];
  const rateNote = RATE_NOTE[row.sold_cost_rate.status];
  const deviation = row.deviation_pp == null ? PENDING : formatPercent(row.deviation_pp, ' pp') + (row.partial ? '*' : '');
  return el(
    'tr',
    {},
    el(
      'td',
      { class: 'mg-name' },
      el('span', { class: 'mg-arrow', 'aria-hidden': 'true', text: '›' }),
      el('strong', { text: row.account }),
      el('small', { text: row.name }),
      el('small', { text: row.services.join(', ') }),
    ),
    el(
      'td',
      { class: 'n' },
      row.bookings == null ? PENDING : formatMoney(row.bookings),
      el('small', { text: `Revenue del periodo: ${formatMoney(row.period_revenue)}` }),
    ),
    el('td', { class: 'n' }, formatMoney(row.operated_revenue), ...(operatedNote ? [el('small', { text: operatedNote })] : [])),
    el('td', { class: 'n', text: formatMoney(row.invoiced) }),
    el('td', { class: 'n', text: formatMoney(row.collected) }),
    el('td', { class: 'n', text: costCell(row) }),
    el('td', { class: 'mg-rate-pending' }, el('strong', { text: PENDING }), ...(rateNote ? [el('small', { text: rateNote })] : [])),
    el('td', { text: formatPercent(row.sold_margin) }),
    el('td', { text: marginCell(row) }),
    el('td', { class: tone(row.deviation_pp) }, el('span', { class: 'mg-deviation', text: deviation })),
    el('td', {}, detailButton),
  );
}

/**
 * @param {HTMLElement} container
 * @param {any[]} opportunities
 * @param {() => Record<string, string>} periodParams
 * @returns {{filter: (text: string) => {shown: number, total: number}}}
 */
export function renderOpportunities(container, opportunities, periodParams) {
  /** @type {{row: HTMLElement, panel: HTMLElement, button: HTMLElement, text: string}[]} */
  const entries = [];
  const body = el('tbody');
  opportunities.forEach((row, index) => {
    const panelId = `mg-panel-${index + 1}`;
    const detail = panel(row, panelId, periodParams);
    const button = el('button', {
      type: 'button',
      class: 'btn btn-ghost',
      'aria-controls': panelId,
      'aria-expanded': 'false',
      text: `Ver IDs ligados (${row.projects.length})`,
    });
    const tr = summaryRow(row, button);
    button.addEventListener('click', () => {
      const open = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!open));
      button.textContent = open ? 'Ver IDs ligados' : 'Ocultar IDs ligados';
      tr.classList.toggle('is-expanded', !open);
      detail.hidden = open;
    });
    body.append(tr, detail);
    entries.push({ row: tr, panel: detail, button, text: plain(`${row.account} ${row.name} ${row.ids.join(' ')}`) });
  });
  if (!opportunities.length) {
    body.append(el('tr', {}, el('td', { colspan: HEADERS.length, text: 'No hay oportunidades en el periodo con el alcance seleccionado.' })));
  }
  container.append(
    el(
      'div',
      { class: 'card mg-results' },
      el(
        'p',
        { class: 'mg-rate-note' },
        el('strong', { text: 'Tarifa de costo vendida: ' }),
        'fuente, unidad y asignación pendientes de validación con Florencia. No se sustituye por la tarifa interna de banda ni se deduce del revenue. Los márgenes actuales conservan su cálculo.',
      ),
      el(
        'div',
        { class: 'mg-scroll' },
        el(
          'table',
          { id: 'mg-table' },
          el('caption', { class: 'sr-only', text: 'Margen vendido y real por oportunidad' }),
          headRow(HEADERS),
          body,
        ),
      ),
    ),
  );
  return {
    filter(text) {
      const needle = plain(text);
      let shown = 0;
      for (const entry of entries) {
        const visible = entry.text.includes(needle);
        entry.row.hidden = !visible;
        entry.panel.hidden = !visible || entry.button.getAttribute('aria-expanded') !== 'true';
        if (visible) shown += 1;
      }
      return { shown, total: entries.length };
    },
  };
}
