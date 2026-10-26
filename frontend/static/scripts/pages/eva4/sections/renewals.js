import { mountReportTable, countryCell } from "../report_table.js";
// @ts-check
// Contratos vencidos o que terminan en los proximos 90 dias.
import { el } from '#app/lib/dom.js';
import { formatDate } from '#app/lib/format.js';
import { buildTable } from '#app/ui/data-table.js';

const URGENCY_PILL = { critical: 'bad', warning: 'warn', ok: 'ok' };

const COLUMNS = [
  { header: 'DM / AM', cell: (/** @type {any} */ r) => `${r.manager} / ${r.account_manager}` },
  { header: 'ID de proyecto', cell: (r) => r.project_id },
  { header: 'País', cell: (r) => r.country },
  { header: 'Fin', cell: (r) => formatDate(r.finish) },
  {
    header: 'Días restantes',
    numeric: true,
    cell: (r) => el('span', { class: `pill ${URGENCY_PILL[/** @type {'critical'|'warning'|'ok'} */ (r.urgency)]}`, text: r.due }),
  },
];

/**
 * @param {HTMLElement} container
 * @param {any} data
 */
export function renderRenewals(container, data) {
  container.append(
    el(
      'section',
      { class: 'eva4-card' },
      el('h2', { text: 'Por renovar' }),
      el('p', {
        class: 'eva4-note',
        text: 'Vencidos y contratos que terminan en los próximos 90 días. Cada combinación de contrato, país, responsables y fecha aparece una sola vez.',
      }),
      el(
        'div',
        { class: 'eva4-scroll' },
        buildTable({
          id: 'eva4-renewals',
          className: 'eva4',
          caption: 'Contratos por renovar',
          columns: COLUMNS,
          rows: data.renewals,
          emptyText: 'Sin renovaciones en este periodo.',
        }),
      ),
    ),
  );
  const table=container.querySelector('#eva4-renewals'),rows=data.renewals.length?[...table.tBodies[0].rows]:[];
  rows.forEach(row=>countryCell(row.cells[2]));
  mountReportTable({table,rows,kind:'renewals',types:{3:'date',4:'number'}});
}
