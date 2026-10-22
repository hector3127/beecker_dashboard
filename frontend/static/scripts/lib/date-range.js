// @ts-check
// Fechas locales del calendario del periodo: sin conversion a UTC.

/** @param {Date} d */
export const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** "2026-10-14" -> Date local. @param {string} text */
export function parseIso(text) {
  const [year, month, day] = text.split('-').map(Number);
  return new Date(year, month - 1, day);
}

/**
 * @param {Date} d
 * @param {number} days
 */
const shift = (d, days) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + days);

/**
 * Rango rapido alrededor de una fecha.
 * @param {string} mode today, yesterday, week, seven, month, lastmonth, quarter o year
 * @param {Date} d
 * @returns {[string, string]}
 */
export function quickRange(mode, d) {
  let start = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  let end = new Date(start);
  if (mode === 'yesterday') start = end = shift(d, -1);
  else if (mode === 'week') {
    start = shift(start, -((start.getDay() + 6) % 7));
    end = shift(start, 6);
  } else if (mode === 'seven') start = shift(start, -6);
  else if (mode === 'month' || mode === 'lastmonth') {
    const month = d.getMonth() - (mode === 'lastmonth' ? 1 : 0);
    start = new Date(d.getFullYear(), month, 1);
    end = new Date(d.getFullYear(), month + 1, 0);
  } else if (mode === 'quarter') {
    const month = Math.floor(d.getMonth() / 3) * 3;
    start = new Date(d.getFullYear(), month, 1);
    end = new Date(d.getFullYear(), month + 3, 0);
  } else if (mode === 'year') {
    start = new Date(d.getFullYear(), 0, 1);
    end = new Date(d.getFullYear(), 11, 31);
  }
  return [iso(start), iso(end)];
}

/**
 * Las 42 celdas de un mes (semanas desde el lunes), con los dias vecinos.
 * @param {number} year
 * @param {number} month 0-11
 */
export function calendarCells(year, month) {
  const first = new Date(year, month, 1);
  const start = shift(first, -((first.getDay() + 6) % 7));
  return Array.from({ length: 42 }, (_, i) => {
    const d = shift(start, i);
    return { key: iso(d), day: d.getDate(), outside: d.getMonth() !== first.getMonth() };
  });
}

/** Tipo de periodo que el servidor entrega (?periodo=) a la pestana del calendario. */
export const TAB_OF_PERIOD = /** @type {Record<string, string>} */ ({ anio: 'year', trimestre: 'quarter', mes: 'month', rango: 'custom' });
