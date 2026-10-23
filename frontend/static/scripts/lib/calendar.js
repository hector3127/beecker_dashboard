// @ts-check
// Calendario con fechas locales: sin conversion a UTC ni dependencias externas.

/** "2026-10-14" desde una fecha local. @param {Date} d */
export const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** Fecha local desde "2026-10-14". @param {string} s */
export const date = (s) => {
  const [year, month, day] = s.split('-').map(Number);
  return new Date(year, month - 1, day);
};

/** @param {Date} d @param {number} n */
const move = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);

/**
 * Rango [inicio, fin] ISO de un atajo (hoy, semana, mes, trimestre, anio...) respecto a `d`.
 * @param {string} mode
 * @param {Date} d
 * @returns {[string, string]}
 */
export function range(mode, d) {
  let start = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  let end = new Date(start);
  if (mode === 'yesterday') start = end = move(d, -1);
  else if (mode === 'week') {
    start = move(start, -((start.getDay() + 6) % 7));
    end = move(start, 6);
  } else if (mode === 'seven') start = move(start, -6);
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
 * Las 42 celdas de un mes (semanas de lunes a domingo, con dias de meses vecinos).
 * @param {number} year @param {number} month 0-11
 */
export function cells(year, month) {
  const first = new Date(year, month, 1);
  const start = move(first, -((first.getDay() + 6) % 7));
  return Array.from({ length: 42 }, (_, i) => {
    const d = move(start, i);
    return { key: iso(d), day: d.getDate(), outside: d.getMonth() !== first.getMonth() };
  });
}
