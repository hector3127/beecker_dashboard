// @ts-check
// Formato de numeros, fechas y texto para mostrar. Los datos llegan crudos de
// la API (numeros y fechas ISO); aqui se decide como se ven.

/** @type {Map<number, Intl.NumberFormat>} */
const FORMATS = new Map();

/**
 * 1284.5 -> "1,284.5"; 12 -> "12". Agrupa miles y recorta decimales.
 * @param {number} value
 * @param {number} [maxDecimals]
 */
export function formatNumber(value, maxDecimals = 2) {
  let format = FORMATS.get(maxDecimals);
  if (!format) {
    format = new Intl.NumberFormat('es-MX', { maximumFractionDigits: maxDecimals });
    FORMATS.set(maxDecimals, format);
  }
  return format.format(value);
}

/** "2026-10-20" -> "20/10/2026". @param {string | null | undefined} iso */
export function formatDate(iso) {
  const found = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
  return found ? `${found[3]}/${found[2]}/${found[1]}` : '';
}

/**
 * "2026-10-22T09:35:12-06:00" -> "22/10/2026 09:35". Se lee la hora tal como
 * viene escrita (la del servidor), sin convertirla a la zona del navegador.
 * @param {string | null | undefined} iso
 * @param {string} [separator] Entre la fecha y la hora.
 */
export function formatDateTime(iso, separator = ' ') {
  const found = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso || '');
  return found ? `${found[3]}/${found[2]}/${found[1]}${separator}${found[4]}:${found[5]}` : '';
}

/** Minusculas y sin acentos, para buscar sin importar como se escribio. @param {string} text */
export const plain = (text) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
