// @ts-check
// Compara todas las cuentas del corte, nunca solo las cinco primeras: la mitad
// superior segun el criterio es «sana» y la inferior «no sana».
import { plain } from '#app/lib/format.js';

export const CRITERIA = ['gross_profit', 'revenue', 'margin'];

/** @param {unknown} value */
export const numeric = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));

/**
 * @param {any[]} accounts
 * @param {string} key gross_profit, revenue o margin.
 * @param {string} [search] Texto del nombre, sin acentos ni mayusculas.
 * @param {{healthy?: 'ascending' | 'descending', unhealthy?: 'ascending' | 'descending'}} [directions]
 */
export function rankAccounts(accounts, key, search = '', directions = {}) {
  if (!CRITERIA.includes(key)) key = 'gross_profit';
  const matches = accounts.filter((account) => plain(String(account.name || '')).includes(plain(search)));
  const eligible = matches.filter((account) => numeric(account[key]));
  const compare = (/** @type {any} */ a, /** @type {any} */ b, /** @type {string} */ direction) =>
    (Number(a[key]) - Number(b[key])) * (direction === 'ascending' ? 1 : -1) || String(a.name).localeCompare(String(b.name), 'es');
  const ranked = [...eligible].sort((a, b) => compare(a, b, 'descending'));
  const split = Math.ceil(ranked.length / 2);
  const groups = { healthy: ranked.slice(0, split), unhealthy: ranked.slice(split) };
  const result = { missing: matches.length - eligible.length, matched: matches.length, eligible: eligible.length, healthy: { count: 0, rows: /** @type {any[]} */ ([]) }, unhealthy: { count: 0, rows: /** @type {any[]} */ ([]) } };
  for (const kind of /** @type {const} */ (['healthy', 'unhealthy'])) {
    const group = groups[kind];
    result[kind] = {
      count: group.length,
      rows: [...group].sort((a, b) => compare(a, b, directions[kind] || (kind === 'healthy' ? 'descending' : 'ascending'))).slice(0, 5),
    };
  }
  return result;
}
