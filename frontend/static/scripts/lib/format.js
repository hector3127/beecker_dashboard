// @ts-check
// Formato de numeros, fechas y texto para mostrar. Los datos llegan crudos de
// la API (numeros y fechas ISO); aqui se decide como se ven.

const NUMBER = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 2 });

/** 1284.5 -> "1,284.5"; 12 -> "12". @param {number} value */
export const formatNumber = (value) => NUMBER.format(value);

/** "2026-10-20" -> "20/10/2026". @param {string | null | undefined} iso */
export function formatDate(iso) {
  const found = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
  return found ? `${found[3]}/${found[2]}/${found[1]}` : '';
}

/**
 * "2026-10-22T09:35:12-06:00" -> "22/10/2026 09:35". Se lee la hora tal como
 * viene escrita (la del servidor), sin convertirla a la zona del navegador.
 * @param {string | null | undefined} iso
 */
export function formatDateTime(iso) {
  const found = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso || '');
  return found ? `${found[3]}/${found[2]}/${found[1]} ${found[4]}:${found[5]}` : '';
}

/** Minusculas y sin acentos, para buscar sin importar como se escribio. @param {string} text */
export const plain = (text) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
