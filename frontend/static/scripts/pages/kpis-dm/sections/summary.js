// @ts-check
// Tarjetas y tabla del corte: TP, T y C de cada Delivery Manager.
import { withReturn } from '#app/data/navigation.js';
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';

/** @param {number | null | undefined} value @param {string} suffix */
export const known = (value, suffix) => (value == null ? '—' : `${formatNumber(value, 1)}${suffix}`);

/** @param {number} percent */
const tone = (percent) => (percent < 40 ? 'lo' : percent >= 80 ? 'hi' : '');

/** @param {string} label @param {string} value @param {string} note @param {boolean} [text] */
const card = (label, value, note, text = false) =>
  el('div', { class: 'card kc' }, el('div', { class: 'kl', text: label }), el('div', { class: `kv${text ? ' txt' : ''}`, text: value }), el('div', { class: 'ke', text: note }));

/** @param {any} dm */
const proportion = (dm) => (dm ? `${dm.on_time_percent}% en tiempo, ${dm.total} proyecto${dm.total === 1 ? '' : 's'}` : '');

/** @param {any} row @param {string} dmUrl */
function managerRow(row, dmUrl) {
  return el(
    'tr',
    {},
    el('td', {}, el('b', {}, el('a', { href: withReturn(dmUrl.replace('DM_SLUG', row.slug)), text: row.name }))),
    el('td', { class: 'n g', text: String(row.total) }),
    el('td', { class: 'n', text: known(row.t, ' d') }),
    el('td', { class: 'n', text: known(row.c, '%') }),
    el('td', { class: `n ${tone(row.on_time_percent)}`, text: `${row.on_time_percent}%` }),
    el('td', { class: 'n', text: String(row.at_risk) }),
    el('td', { class: 'n', text: String(row.critical) }),
  );
}

/**
 * @param {HTMLElement} container
 * @param {any} summary
 * @param {string} dmUrl
 */
export function renderSummary(container, summary, dmUrl) {
  const { totals, best, worst } = summary;
  const rows = summary.rows.length
    ? summary.rows.map((/** @type {any} */ r) => managerRow(r, dmUrl))
    : [el('tr', {}, el('td', { colspan: 7, class: 'na', text: 'Sin proyectos en ejecución.' }))];
  const footer = el(
    'tr',
    {},
    el('td', { text: 'Total' }),
    el('td', { class: 'n g', text: String(totals.total) }),
    el('td', { class: 'n', text: known(totals.t, ' d') }),
    el('td', { class: 'n', text: known(totals.c, '%') }),
    el('td', { class: `n ${tone(totals.on_time_percent)}`, text: `${totals.on_time_percent}%` }),
    el('td', { class: 'n', text: String(totals.at_risk) }),
    el('td', { class: 'n', text: String(totals.critical) }),
  );
  container.append(
    el(
      'section',
      { class: 'kpi-cards' },
      card('Consumo promedio (C)', known(totals.c, '%'), `Horas sobre presupuesto · T: ${totals.t == null ? '—' : `${formatNumber(totals.t, 1)} días`}`),
      card('Carga total (TP)', String(totals.total), `${totals.on_time_percent}% en tiempo`),
      card('Mayor proporción en tiempo', best ? best.name : '—', proportion(best), true),
      card('Menor proporción en tiempo', worst ? worst.name : '—', proportion(worst), true),
    ),
    el(
      'div',
      { class: 'card' },
      el('h2', { text: 'Por Delivery Manager' }),
      el('div', { class: 'hs', text: 'TP: proyectos en ejecución. T: desviación promedio en días. C: avance promedio. En tiempo: % de sus proyectos con salud en tiempo.' }),
      el(
        'div',
        { class: 'table-scroll' },
        el('table', { id: 'kpi-managers' }, el('thead', {}, el('tr', {}, ...['DM', 'TP', 'T', 'C', 'En tiempo', 'En riesgo', 'Críticos'].map((h) => el('th', { scope: 'col', text: h })))), el('tbody', {}, ...rows), el('tfoot', {}, footer)),
      ),
      el('p', { class: 'note', text: 'En tiempo: rojo menos de 40%, verde 80% o más.' }),
    ),
  );
}
