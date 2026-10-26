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

const PENDING = 'Pendiente';

/**
 * Cifra compacta sin simbolo: 1500 -> "1K", 2.5e6 -> "2.5M", 1.2e9 -> "1.2B".
 * Trunca (no redondea) como el resto del portal; un dato faltante es "Pendiente", nunca cero.
 * @param {number | string | null | undefined} value
 */
export function formatCompact(value) {
  // Decimal amounts are serialized as strings by the finance API.
  if (typeof value === 'string') {
    const decimal = value.trim();
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(decimal)) return PENDING;
    value = Number(decimal);
  }
  if (typeof value !== 'number' || !Number.isFinite(value)) return PENDING;
  const size = Math.abs(value);
  const unit = size >= 1e9 ? 1e9 : size >= 1e6 ? 1e6 : size >= 1e3 ? 1e3 : 1;
  const suffix = { 1e9: 'B', 1e6: 'M', 1e3: 'K', 1: '' }[unit];
  const precision = unit >= 1e6 ? 100 : 1;
  const shown = Math.trunc((value / unit) * precision) / precision;
  return shown.toLocaleString('en-US', { maximumFractionDigits: unit >= 1e6 ? 2 : 0 }) + suffix;
}

/**
 * Dolares compactos: 1500 -> "$1K"; negativos "-$1K"; faltante "Pendiente".
 * @param {number | string | null | undefined} value
 */
export function formatMoney(value) {
  const text = formatCompact(value);
  if (text === PENDING) return text;
  return text.startsWith('-') ? `-$${text.slice(1)}` : `$${text}`;
}

/**
 * Porcentaje con decimales fijos; "Pendiente" si falta.
 * @param {number | null | undefined} value
 * @param {string} [unit] "%" o " pp".
 * @param {number} [digits]
 */
export function formatPercent(value, unit = '%', digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(value)) return PENDING;
  return `${value.toFixed(digits)}${unit}`;
}
