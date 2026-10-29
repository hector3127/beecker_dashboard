import { mountReportTable, countryCell, clientCell } from "../report_table.js?v=20261029-search";
// @ts-check
// Tabla principal de EVA-04: procesos activos con su consumo de horas.
import { el } from '#app/lib/dom.js';
import { formatDate, formatNumber } from '#app/lib/format.js';
import { buildTable } from '#app/ui/data-table.js';

const NO_LIMIT = 'Sin límite para este servicio';
const NO_MATCH = 'Sin coincidencia en Clockify';
const NO_DATA = 'Sin dato';

/** "Sin dato", con el motivo al pasar el cursor. @param {string} reason */
const missing = (reason) => el('span', { title: reason, text: NO_DATA });
/** @param {number | null} value @param {string} text */
const hours = (value, text) => (value === null ? missing(text) : formatNumber(value));
/** @param {unknown} value */
const raw = (value) => (value === null ? missing('La fuente no trae el dato.') : String(value));
/** @param {string | null} iso */
const day = (iso) => formatDate(iso) || '—';

const COLUMNS = [
  { header: 'Delivery Manager', cell: (/** @type {any} */ r) => r.manager },
  { header: 'Country', cell: (r) => r.country },
  { header: 'Client', cell: (r) => r.client },
  { header: 'BOT ID', cell: (r) => r.bot },
  { header: 'Service', cell: (r) => r.service },
  { header: 'Process Name', cell: (r) => r.process },
  {
    header: 'Status ROC',
    cell: (r) => el('span', { class: `eva4-pill ${r.status_code}`, text: r.status }),
  },
  { header: 'Start', cell: (r) => day(r.start) },
  { header: 'Finish', cell: (r) => day(r.finish) },
  { header: 'Average Limit', numeric: true, cell: (r) => hours(r.average_limit, NO_LIMIT) },
  { header: 'Invested Hours', numeric: true, cell: (r) => hours(r.invested_hours, NO_MATCH) },
  {
    header: 'Hours Balance',
    numeric: true,
    cell: (r) => hours(r.hours_balance, 'Sin balance: falta el límite o las horas.'),
    cellClass: (r) => (r.hours_balance !== null && r.hours_balance < 0 ? 'critical' : ''),
  },
  { header: 'Hours Package Limit', numeric: true, cell: (r) => r.package_limit === null && String(r.service).trim().toLowerCase() !== 'raas' ? 'No aplica' : raw(r.package_limit) },
  { header: 'Available Hours Package', numeric: true, cell: (r) => raw(r.package_available) },
  { header: 'Risk', cell: (r) => r.risk ?? '—' },
];

/**
 * Pinta la seccion y devuelve el filtro de busqueda sobre sus filas.
 * @param {HTMLElement} container
 * @param {any} data
 * @param {Node[]} toolbar Contador, que van antes de la tabla.
 * @returns {{filter: (text: string) => {shown: number, total: number}}}
 */
export function renderProcesses(container, data, toolbar) {
  const table = buildTable({
    id: 'eva4-processes',
    className: 'eva4 eva4-detail',
    caption: `Procesos de automatización con su consumo de horas del mes ${data.month}`,
    columns: COLUMNS,
    rows: data.processes,
    emptyText: 'No hay procesos activos.',
  });
  const { notes } = data;
  const note = (/** @type {string} */ text) => el('p', { class: 'eva4-note', text });
  container.append(
    el(
      'section',
      { class: 'eva4-card', 'aria-labelledby': 'eva4-processes-title' },
      el('h2', { id: 'eva4-processes-title', text: 'Procesos y consumo por servicio' }),
      note(
        'Consumo mensual de la base Clockify del Sheet. Hours Balance = Average Limit − Invested Hours; los excesos se muestran en negativo. Average Limit por servicio: ROC 30, AER 160, RaaS 40, SaaS 80, T&M 160.',
      ),
      notes.missing_columns.length ? note(`Columnas pendientes de fuente: ${notes.missing_columns.join(', ')}.`) : '',
      notes.unmatched_tasks
        ? note(`${notes.unmatched_tasks} procesos no tienen coincidencia exacta de tarea en la base. Su consumo se muestra como «Sin dato» para evitar asignar horas de otro proceso.`)
        : '',
      ...toolbar,
      el('div', { class: 'eva4-scroll' }, table),
    ),
  );
  const rows = data.processes.length ? [.../** @type {NodeListOf<HTMLElement>} */ (table.querySelectorAll('tbody tr'))] : [];
  rows.forEach(row=>{countryCell(row.cells[1]);clientCell(row.cells[2]);});
  const controller = mountReportTable({table,rows,kind:'processes',types:Object.fromEntries(COLUMNS.map((column,index)=>[index,[7,8].includes(index)?'date':column.numeric?'number':'text'])),onCount:({shown,total})=>{toolbar[0].textContent=`${shown} de ${total} procesos activos`;}});
  const input = el('input', {
    id: 'eva4-process-search', type: 'search',
    placeholder: 'Ej. Brandon Nestlé, AIN.002 o nombre del proceso',
    'aria-controls': 'eva4-processes',
    oninput: () => controller.filter(input.value),
  });
  const search = el('div', { class: 'eva4-process-search' },
    el('label', { for: 'eva4-process-search', text: 'Buscar en procesos' }),
    el('div', { class: 'eva4-process-search-controls' }, input,
      el('button', { type: 'button', text: 'Limpiar búsqueda', onclick: () => {
        input.value = ''; controller.filter(''); input.focus();
      } })),
    el('span', { class: 'eva4-note', text: 'Busca palabras en todas las columnas, sin distinguir mayúsculas ni acentos.' }));
  table.closest('.eva4-scroll').before(search);
  return controller;
}
