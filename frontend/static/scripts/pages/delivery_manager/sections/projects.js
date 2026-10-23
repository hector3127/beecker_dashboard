// @ts-check
// Tabla de proyectos del Delivery Manager; los que piden atencion van primero.
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { icon } from './kpis.js';

const DASH = '—';
const HEADERS = [
  'ID del proyecto',
  'Proyecto',
  'Cuenta',
  'Servicio',
  'Inicio',
  'Fin',
  'Presupuesto (h)',
  'Consumo (h)',
  'Inv. operativa (h)',
  'Inv. comercial (h)',
  'Estado',
  'Avance',
  'ETC (h)',
  'Renovación (días)',
  'Riesgo abierto',
];

/** @param {number | null | undefined} value */
const hours = (value) => (value === null || value === undefined ? DASH : formatNumber(value, 2));
/** @param {string} template @param {string} placeholder @param {string} value */
const link = (template, placeholder, value) => template.replace(placeholder, encodeURIComponent(value));

/** Etiqueta con color: bueno, advertencia o malo. @param {string} tone @param {string} text */
const value = (tone, text) => el('span', { class: `dm-value ${tone}`, text });

/**
 * @param {any} row
 * @param {{project: string, account: string}} urls
 */
function projectRow(row, urls) {
  const project = link(urls.project, 'project-placeholder', row.project_id);
  const progress = row.progress_percent;
  const num = (/** @type {Node | string} */ content) => el('td', { class: 'num' }, content);
  return el(
    'tr',
    { class: row.row_class || null },
    el('td', {}, el('a', { href: project, text: row.project_id })),
    el('td', {}, el('b', {}, el('a', { href: project, text: row.name }))),
    el(
      'td',
      {},
      row.client ? el('a', { href: link(urls.account, 'account-placeholder', row.account_slug), text: row.client }) : 'Sin cuenta',
    ),
    el('td', { text: row.service }),
    el('td', { text: row.start || 'Sin fecha' }),
    el('td', { text: row.end || 'Sin fecha' }),
    num(hours(row.budget)),
    num(hours(row.burn)),
    num(hours(row.investment_operational)),
    num(hours(row.investment_commercial)),
    el(
      'td',
      {},
      el('span', { class: `st s-${row.status_code}` }, el('i'), row.status_label),
      ...(row.detail ? [el('small', { text: row.detail })] : []),
    ),
    num(progress === null ? DASH : value(progress > 100 ? 'bad' : progress >= 85 ? 'warning' : 'good', `${formatNumber(progress, 1)}%`)),
    num(row.etc_hours === null ? DASH : value(row.etc_hours <= 0 ? 'bad' : 'good', formatNumber(row.etc_hours, 2))),
    num(row.renewal_days === null ? DASH : value(row.renewal_days < 30 ? 'bad' : 'good', String(row.renewal_days))),
    num(row.risk),
  );
}

/** @param {string} name */
function heading(name) {
  return el(
    'div',
    { class: 'section-head' },
    icon('folder'),
    el('div', {}, el('h2', { text: `Proyectos de ${name}` }), el('div', { class: 'hs', text: 'Los que necesitan atención aparecen primero' })),
  );
}

/** @param {string} name */
export function loadingTable(name) {
  return [heading(name), el('div', { class: 'vacio', role: 'status', text: 'Cargando proyectos, avance y riesgos…' })];
}

/**
 * @param {any} data
 * @param {{project: string, account: string}} urls
 */
export function renderTable(data, urls) {
  const body = data.rows.length
    ? data.rows.map((/** @type {any} */ row) => projectRow(row, urls))
    : [el('tr', {}, el('td', { colspan: 15, class: 'vacio', text: 'Sin proyectos en ejecución ni suspendidos.' }))];
  return [
    heading(data.name),
    el(
      'div',
      { class: 'table-scroll' },
      el('table', {}, el('thead', {}, el('tr', {}, ...HEADERS.map((text) => el('th', { text })))), el('tbody', {}, ...body)),
    ),
  ];
}
