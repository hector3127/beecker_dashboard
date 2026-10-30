// @ts-check
// Capacidad instalada del equipo: calculos y filtros sin DOM.
// Fuente: Bandas/rol + Clockify del mes (ver apps/capacidad/services/team_capacity.py).

/** @param {any} value */
export const norm = (value) =>
  String(value || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();

/** @param {any} value */
export const fmt = (value) =>
  Number(value || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 });

/** @param {string} value ISO AAAA-MM-DD @returns {string} DD/MM */
export const date = (value) => (value ? `${value.slice(8, 10)}/${value.slice(5, 7)}` : '—');

/** @param {string} value ISO AAAA-MM-DD @returns {string} DD/MM/AAAA */
export const fullDate = (value) =>
  /^\d{4}-\d{2}-\d{2}$/.test(value || '') ? `${value.slice(8, 10)}/${value.slice(5, 7)}/${value.slice(0, 4)}` : '—';

/** @param {string} iso */
export const isWeekend = (iso) => {
  const day = new Date(iso + 'T00:00:00Z').getUTCDay();
  return day === 0 || day === 6;
};

/**
 * Indicadores del mes completo; la jornada se puede cambiar sin volver a leer.
 * @param {any} data respuesta de la API @param {number} workday
 */
export function indicators(data, workday) {
  const people = data.personas || [];
  const perPerson = data.diasHabiles * workday;
  const base = people.length * perPerson;
  const registered = people.reduce((/** @type {number} */ n, /** @type {any} */ p) => n + p.total, 0);
  return {
    people: people.length,
    withHours: people.filter((/** @type {any} */ p) => p.total > 0).length,
    over: people.filter((/** @type {any} */ p) => p.total > perPerson).length,
    base,
    registered,
    billable: people.reduce((/** @type {number} */ n, /** @type {any} */ p) => n + p.facturables, 0),
    balance: base - registered,
    utilization: base ? (registered / base) * 100 : null,
  };
}

/** @param {any} item @param {any} st */
const matches = (item, st) =>
  (!st.rol || item.rol === st.rol) &&
  (!st.banda || item.banda === st.banda) &&
  (!st.q ||
    norm([item.nombre, item.idProyecto, item.proyecto, item.dm, item.clockifyId].join(' ')).includes(
      norm(st.q),
    ));

/** Filas de la matriz que pasan los filtros. @param {any} data @param {any} st */
export const selectedRows = (data, st) => (data.filas || []).filter((/** @type {any} */ r) => matches(r, st));

/** Personas que pasan los filtros. @param {any} data @param {any} st */
export const selectedPeople = (data, st) => (data.personas || []).filter((/** @type {any} */ p) => matches(p, st));

/** Valores distintos de un campo, para llenar los filtros. @param {any} data @param {'rol'|'banda'} field */
export const options = (data, field) =>
  [...new Set((data.personas || []).map((/** @type {any} */ p) => p[field]).filter(Boolean))].sort();

/** Todas las filas de una persona, sin filtros. @param {any} data @param {string} name */
export function resourceDetail(data, name) {
  const rows = (data.filas || []).filter((/** @type {any} */ r) => r.nombre === name);
  return { days: data.dias || [], rows, person: (data.personas || []).find((/** @type {any} */ p) => p.nombre === name) };
}

/** @param {any} value */
const cell = (value) => '"' + String(value == null ? '' : value).replace(/"/g, '""') + '"';

/** CSV de las filas visibles; protege contra formulas de hoja de calculo. @param {any} data @param {any[]} rows */
export function csv(data, rows) {
  const head = [
    'Recurso', 'Rol', 'Banda', 'Delivery Manager', 'ID Proyecto', 'Proyecto', 'Inicio', 'Fin',
    'Concepto', 'Facturable', 'Cargabilidad', 'Capacidad disponible',
    'Total mes',
    ...(data.dias || []),
  ];
  const safe = (/** @type {any} */ v) => (typeof v === 'string' && /^[=+\-@]/.test(v) ? "'" + v : v);
  const records = rows.map((r) => [
    r.nombre, r.rol, r.banda, r.dm || '-', r.idProyecto, r.proyecto, r.inicio, r.fin,
    r.concepto, r.facturable, r.cargabilidad, r.capacidad,
    r.total,
    ...(data.dias || []).map((/** @type {string} */ d) => r.daily[d] || ''),
  ].map(safe));
  return '﻿' + [head, ...records].map((row) => row.map(cell).join(',')).join('\r\n');
}
