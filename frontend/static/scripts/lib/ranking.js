// @ts-check
// Comparacion de cuentas: parte las que tienen dato en mitad superior e
// inferior segun el criterio. Son posiciones relativas, no una clasificacion.
import { plain } from '#app/lib/format.js';

export const CRITERIA = /** @type {const} */ (['gross_profit', 'revenue', 'margin']);
export const MAX_ROWS = 5;

/** @typedef {{name: string, revenue?: number | null, gross_profit?: number | null, margin?: number | null, projects?: number, partial?: boolean}} RankedAccount */

/** @param {unknown} value */
const numeric = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));

/**
 * @param {RankedAccount[]} accounts
 * @param {string} key gross_profit, revenue o margin
 * @param {string} [search]
 * @param {{top?: 'ascending' | 'descending', bottom?: 'ascending' | 'descending'}} [directions]
 */
export function rankAccounts(accounts, key, search = '', directions = {}) {
  const criterion = /** @type {'gross_profit' | 'revenue' | 'margin'} */ (CRITERIA.includes(/** @type {any} */ (key)) ? key : 'gross_profit');
  const matches = accounts.filter((a) => plain(a.name).includes(plain(search)));
  const eligible = matches.filter((a) => numeric(a[criterion]));
  /** @param {RankedAccount} a @param {RankedAccount} b @param {string} direction */
  const compare = (a, b, direction) =>
    (Number(a[criterion]) - Number(b[criterion])) * (direction === 'ascending' ? 1 : -1) || String(a.name).localeCompare(String(b.name), 'es');
  const ranked = [...eligible].sort((a, b) => compare(a, b, 'descending'));
  const split = Math.ceil(ranked.length / 2);
  /** @param {RankedAccount[]} group @param {string} direction */
  const view = (group, direction) => ({ count: group.length, rows: [...group].sort((a, b) => compare(a, b, direction)).slice(0, MAX_ROWS) });
  return {
    criterion,
    matched: matches.length,
    eligible: eligible.length,
    missing: matches.length - eligible.length,
    partial: eligible.filter((a) => a.partial).length,
    top: view(ranked.slice(0, split), directions.top || 'descending'),
    bottom: view(ranked.slice(split), directions.bottom || 'ascending'),
  };
}
