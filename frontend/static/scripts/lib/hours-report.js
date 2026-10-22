// @ts-check
// Consumo de horas por mes de un Delivery Manager: escala de la grafica y CSV
// del detalle. Sin DOM, para probarlo con node.

export const HOUR_KEYS = /** @type {const} */ (['billable', 'operational', 'commercial']);

/**
 * @typedef {object} HoursProject
 * @property {string} id
 * @property {string} name
 * @property {string} [client]
 * @property {string} [service]
 * @property {number | null} [project_budget]
 * @property {number} billable
 * @property {number} operational
 * @property {number} commercial
 * @property {number} total
 */
/**
 * @typedef {object} HoursMonth
 * @property {string} label
 * @property {number} total
 * @property {number} [budget]
 * @property {number} billable
 * @property {number} operational
 * @property {number} commercial
 * @property {number} [budget_missing]
 * @property {HoursProject[]} projects
 */

/**
 * Tope del eje vertical y sus 5 marcas: el maximo, redondeado hacia arriba a
 * medias potencias de diez.
 * @param {HoursMonth[]} months
 */
export function hoursScale(months) {
  const limit = Math.max(1, ...months.map((m) => Math.max(m.total, m.budget || 0)));
  const step = Math.pow(10, Math.floor(Math.log10(limit))) / 2;
  const top = Math.ceil(limit / step) * step;
  return { top, ticks: [0, 1, 2, 3, 4].map((n) => (top * n) / 4) };
}

/** Un valor de celda a texto CSV; los que empiezan como formula se neutralizan. @param {unknown} value */
export function csvCell(value) {
  let text = String(value ?? '');
  if (/^[=+@-]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

/** CSV del detalle de un mes, con BOM para que Excel lo abra en UTF-8. @param {HoursMonth} month */
export function monthCsv(month) {
  const rows = [
    ['ID', 'Proyecto', 'Cuenta', 'Servicio', 'Presupuesto proyecto', 'Facturables', 'Inv. operativa', 'Inv. comercial', 'Total'],
    ...month.projects.map((p) => [p.id, p.name, p.client, p.service, p.project_budget, p.billable, p.operational, p.commercial, p.total]),
  ];
  return `﻿${rows.map((row) => row.map(csvCell).join(',')).join('\r\n')}`;
}
