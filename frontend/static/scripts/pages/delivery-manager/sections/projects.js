// @ts-check
// Proyectos del Delivery Manager: los que necesitan atencion, primero.
import { withReturn } from '#app/data/navigation.js';
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';

const HEADERS = ['ID del proyecto', 'Proyecto', 'Cuenta', 'Servicio', 'Inicio', 'Fin', 'Presupuesto (h)', 'Consumo (h)', 'Inv. operativa (h)', 'Inv. comercial (h)', 'Estado', 'Avance', 'ETC (h)', 'Renovación (días)', 'Riesgo abierto'];
const ROW_CLASS = { r: 'critical', a: 'at-risk' };

/** @param {number | null | undefined} value */
const hoursOrDash = (value) => (value == null ? '—' : formatNumber(value));

/**
 * @param {number | null | undefined} value
 * @param {string} tone good | warning | bad
 * @param {string} text
 */
const valueCell = (value, tone, text) =>
  el('td', { class: 'n' }, value == null ? '—' : el('span', { class: `dm-value ${tone}`, text }));

/**
 * @param {any} row
 * @param {{project: string, account: string}} urls
 */
function projectRow(row, urls) {
  const link = withReturn(urls.project.replace('PROJECT_ID', encodeURIComponent(row.project_id)));
  const progress = row.progress_percent;
  return el(
    'tr',
    { class: ROW_CLASS[/** @type {'r' | 'a'} */ (row.status_code)] || '' },
    el('td', {}, el('a', { href: link, text: row.project_id })),
    el('td', {}, el('b', {}, el('a', { href: link, text: row.name }))),
    el('td', {}, row.client ? el('a', { href: withReturn(urls.account.replace('ACCOUNT_SLUG', row.account_slug)), text: row.client }) : 'Sin cuenta'),
    el('td', { text: row.service || '' }),
    el('td', { text: row.start || 'Sin fecha' }),
    el('td', { text: row.end || 'Sin fecha' }),
    el('td', { class: 'n', text: formatNumber(row.budget ?? 0) }),
    el('td', { class: 'n', text: hoursOrDash(row.burn) }),
    el('td', { class: 'n', text: hoursOrDash(row.investment_operational) }),
    el('td', { class: 'n', text: hoursOrDash(row.investment_commercial) }),
    el('td', {}, el('span', { class: `st s-${row.status_code}` }, el('i'), row.status_label), ...(row.detail ? [el('small', { text: row.detail })] : [])),
    valueCell(progress, progress > 100 ? 'bad' : progress >= 85 ? 'warning' : 'good', `${formatNumber(progress, 1)}%`),
    valueCell(row.etc_hours, row.etc_hours <= 0 ? 'bad' : 'good', formatNumber(row.etc_hours ?? 0)),
    valueCell(row.renewal_days, row.renewal_days < 30 ? 'bad' : 'good', String(row.renewal_days)),
    el('td', { class: 'n', text: row.risk }),
  );
}

/**
 * @param {HTMLElement} container
 * @param {any} data
 * @param {{project: string, account: string}} urls
 */
export function renderProjects(container, data, urls) {
  const rows = data.rows.length
    ? data.rows.map((/** @type {any} */ row) => projectRow(row, urls))
    : [el('tr', {}, el('td', { colspan: HEADERS.length, class: 'vacio', text: 'Sin proyectos en ejecución ni suspendidos.' }))];
  container.replaceChildren(
    el('div', { class: 'section-head' }, el('div', {}, el('h2', { text: `Proyectos de ${data.name}` }), el('div', { class: 'hs', text: 'Los que necesitan atención aparecen primero' }))),
    el('div', { class: 'table-scroll' }, el('table', { id: 'dm-projects' }, el('caption', { class: 'sr-only', text: `Proyectos de ${data.name}` }), el('thead', {}, el('tr', {}, ...HEADERS.map((h) => el('th', { scope: 'col', text: h })))), el('tbody', {}, ...rows))),
  );
}
