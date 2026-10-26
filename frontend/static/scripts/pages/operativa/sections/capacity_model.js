// @ts-check
// model: operativa/sections/capacity. Original data, ordering and interactions are preserved.
import { formatNumber } from "#app/lib/format.js";
export const NO_VALUE = "—";
export const RESTRICTED =
  "Cifras del equipo completo: no disponibles con tu acceso.";
/**
 * @param {any} value
 */
export const known = (value) =>
  typeof value === "number" && Number.isFinite(value);
/**
 * @param {any} value
 * @param {number} digits
 */
export const hours = (value, digits = 2) =>
  known(value) ? `${formatNumber(value, digits)} h` : NO_VALUE;
/**
 * @param {number} billable
 * @param {number} base
 */
export function meterPercent(billable, base) {
  return base
    ? Math.min(100, Math.max(0, Math.round((billable / base) * 100)))
    : 0;
}
/**
 * @param {any} value
 * @param {number} base
 */
export function ratio(value, base) {
  return known(value) && known(base) && base > 0
    ? `${formatNumber((value / base) * 100, 1)}% de la capacidad`
    : "";
}
