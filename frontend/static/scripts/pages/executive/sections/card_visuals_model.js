// @ts-check
// model: executive/sections/card_visuals. Original data, ordering and interactions are preserved.
/**
 * @param {any} value
 */
export const numeric = (value) =>
  value !== null &&
  value !== undefined &&
  value !== "" &&
  Number.isFinite(Number(value));

/** @param {{revenue: unknown, cost?: unknown}[]} months @param {boolean} margin */
/**
 * @param {{revenue: unknown, cost?: unknown}[]} months
 * @param {boolean} margin
 */
export function monthlyValues(months, margin) {
  return months.map((row) => {
    if (!numeric(row.revenue)) return null;
    if (!margin) return Number(row.revenue);
    return numeric(row.cost) && Number(row.revenue) > 0
      ? ((Number(row.revenue) - Number(row.cost)) / Number(row.revenue)) * 100
      : null;
  });
}
