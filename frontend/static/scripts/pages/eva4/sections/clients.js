import { mountReportTable, clientCell } from "../report_table.js";
// @ts-check
// Procesos activos y suspendidos por cliente y servicio.
import { el } from '#app/lib/dom.js';

/** @param {string} text @param {boolean} [numeric] */
const th = (text, numeric = false) => el('th', { scope: 'col', class: numeric ? 'n' : '', text });
/** @param {number} value @param {string} [tag] */
const count = (value, tag = 'td') => el(tag, { class: 'n', text: value });

/**
 * @param {HTMLElement} container
 * @param {any} data
 */
export function renderClients(container, data) {
  const { clients, summary } = data;
  const services = clients.services.length;
  const head = el(
    'thead',
    {},
    el(
      'tr',
      {},
      el('th', { rowspan: 2, scope: 'col', text: 'Cliente' }),
      el('th', { colspan: services, scope: 'colgroup', text: 'Servicios de automatización' }),
      el('th', { rowspan: 2, scope: 'col', text: 'Total' }),
      el('th', { colspan: 2, scope: 'colgroup', text: 'Estado' }),
    ),
    el('tr', {}, ...clients.services.map((/** @type {string} */ name) => th(name, true)), th('Suspendidos', true), th('Activos', true)),
  );
  const rows = clients.rows.map((/** @type {any} */ row) =>
    el(
      'tr',
      {},
      el('td', { text: row.name }),
      ...row.counts.map((/** @type {number} */ n) => count(n)),
      el('td', { class: 'n' }, el('b', { text: row.total })),
      count(row.suspended),
      count(row.active),
    ),
  );
  const totals = el(
    'tr',
    { class: 'total' },
    el('td', { text: 'Total' }),
    ...clients.service_totals.map((/** @type {number} */ n) => count(n)),
    count(summary.total),
    count(summary.suspended),
    count(summary.active),
  );
  container.append(
    el(
      'section',
      { class: 'eva4-card' },
      el('h2', { text: 'Servicios y estado por cliente' }),
      el('p', {
        class: 'eva4-note',
        text: 'Procesos activos y suspendidos, contados como filas de ROC. Los servicios mantienen la clasificación del Sheet.',
      }),
      el(
        'div',
        { class: 'eva4-scroll' },
        el('table', { id: 'eva4-clients', class: 'eva4' }, el('caption', { class: 'sr-only', text: 'Procesos por cliente y servicio' }), head, el('tbody', {}, ...rows, totals)),
      ),
    ),
  );
  const table=container.querySelector('#eva4-clients');
  rows.forEach(row=>{clientCell(row.cells[0]);const cell=row.cells[row.cells.length-1];cell.replaceChildren(el('span',{class:'eva4-active-count',text:cell.textContent}));});
  totals.title='Total del periodo completo';
  mountReportTable({table,rows,totals,kind:'clients',types:Object.fromEntries(Array.from({length:services+4},(_,index)=>[index,index?'number':'text']))});
}
