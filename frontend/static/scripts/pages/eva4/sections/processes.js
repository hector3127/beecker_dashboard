// @ts-check
// Tabla principal de EVA-04: procesos activos con su consumo de horas.
import { el } from '#app/lib/dom.js';
import { formatDate, formatNumber, plain } from '#app/lib/format.js';
import { buildTable } from '#app/ui/data-table.js';

const NO_LIMIT = 'Sin límite para este servicio';
const NO_MATCH = 'Sin coincidencia en Clockify';
const STATUS_PILL = { active: 'ok', suspended: 'bad' };

/** Texto atenuado cuando la fuente no trae el dato. @param {string} text */
const missing = (text) => el('span', { class: 'eva4-na', text });
/** @param {number | null} value @param {string} text */
const hours = (value, text) => (value === null ? missing(text) : formatNumber(value));
/** @param {unknown} value */
const raw = (value) => (value === null ? missing('—') : String(value));
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
    cell: (r) => el('span', { class: `pill ${STATUS_PILL[/** @type {'active'|'suspended'} */ (r.status_code)]}`, text: r.status }),
  },
  { header: 'Start', cell: (r) => day(r.start) },
  { header: 'Finish', cell: (r) => day(r.finish) },
  { header: 'Average Limit', numeric: true, cell: (r) => hours(r.average_limit, NO_LIMIT) },
  { header: 'Invested Hours', numeric: true, cell: (r) => hours(r.invested_hours, NO_MATCH) },
  {
    header: 'Hours Balance',
    numeric: true,
    cell: (r) => hours(r.hours_balance, '—'),
    cellClass: (r) => (r.hours_balance !== null && r.hours_balance < 0 ? 'critical' : ''),
  },
  { header: 'Hours Package Limit', numeric: true, cell: (r) => raw(r.package_limit) },
  { header: 'Available Hours Package', numeric: true, cell: (r) => raw(r.package_available) },
  { header: 'Risk', cell: (r) => r.risk ?? '—' },
];

/** @param {string} label @param {string} text @param {string} [count] */
const item = (label, text, count = '') => el('li', {}, el('b', { text: label }), count, text);

/** @param {any} data */
function explanation(data) {
  const { notes, month } = data;
  const count = (/** @type {number} */ n) => (n ? ` (${n} procesos)` : '');
  return el(
    'details',
    { class: 'eva4-how' },
    el('summary', { text: 'Cómo se calcula' }),
    el(
      'ul',
      { class: 'note' },
      item('Procesos', ': solo se muestran los de estado Activo en la hoja ROC.'),
      item(
        'Invested Hours',
        `: horas de Clockify del mes ${month} (todas las etiquetas) en el proyecto del ROC ID, de las tareas que son el BOT ID o empiezan con él («AMK.012», «1386 - Sending VES»). Si el proyecto se llama distinto en Clockify, se liga en la hoja Clockify_Vinculos.`,
      ),
      item('Average Limit', ': lo fija el servicio. ROC 30, AER 160, RaaS 40, SaaS 80, T&M 160.'),
      item('Hours Balance', ' = Average Limit − Invested Hours. Un valor negativo es un exceso.'),
      item(
        'Sin coincidencia en Clockify',
        ': no se encontró el proyecto del ROC ID en Clockify. Un BOT sin horas en un proyecto que sí existe vale 0.',
        count(notes.unmatched_tasks),
      ),
      item(
        'Sin límite para este servicio',
        ': el servicio no tiene Average Limit definido, así que no hay balance.',
        count(notes.missing_limits),
      ),
      el(
        'li',
        {},
        el('b', { text: 'Hours Package Limit' }),
        ': 80 por defecto en RaaS cuando la fuente no lo trae. ',
        el('b', { text: 'Available Hours Package' }),
        ': la columna «Hours Consumed» de la hoja ROC.',
      ),
      item('—', ': la fuente no trae el dato.'),
    ),
  );
}

/**
 * Pinta la seccion y devuelve el filtro de busqueda sobre sus filas.
 * @param {HTMLElement} container
 * @param {any} data
 * @returns {{filter: (text: string) => {shown: number, total: number}}}
 */
export function renderProcesses(container, data) {
  const table = buildTable({
    id: 'eva4-processes',
    className: 'eva4 eva4-detail',
    caption: `Procesos de automatización con su consumo de horas del mes ${data.month}`,
    columns: COLUMNS,
    rows: data.processes,
    emptyText: 'No hay procesos activos.',
  });
  container.append(
    el(
      'section',
      { class: 'card', 'aria-labelledby': 'eva4-processes-title' },
      el('h2', { id: 'eva4-processes-title', text: 'Procesos y consumo por servicio' }),
      data.notes.missing_columns.length
        ? el('p', { class: 'note', text: `Columnas pendientes de fuente: ${data.notes.missing_columns.join(', ')}.` })
        : '',
      explanation(data),
      el('div', { class: 'eva4-scroll' }, table),
    ),
  );
  const rows = data.processes.length ? [.../** @type {NodeListOf<HTMLElement>} */ (table.querySelectorAll('tbody tr'))] : [];
  return {
    filter(text) {
      const wanted = plain(text);
      let shown = 0;
      for (const row of rows) {
        row.hidden = !plain(row.textContent || '').includes(wanted);
        if (!row.hidden) shown += 1;
      }
      return { shown, total: rows.length };
    },
  };
}
