// @ts-check
// model: billability/reference. Original data, ordering and interactions are preserved.
/**
 * @param {any} value
 */
export const number = (value) => {
  if (value === "" || value == null) return null;
  const n = Number(String(value).replace(",", "."));
  return Number.isFinite(n) ? n : null;
};
/**
 * @param {any} value
 * @param {number} digits
 */
export const fmt = (value, digits = 1) =>
  value == null || !Number.isFinite(Number(value))
    ? "—"
    : Number(value).toLocaleString("es-MX", { maximumFractionDigits: digits });
