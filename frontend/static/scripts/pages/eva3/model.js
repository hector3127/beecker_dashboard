// @ts-check
// Numeric rules retained from the previous deferred-consumption script.
/**
 * @param {number} n
 */
export const fmt = (n) =>
  Number(n).toLocaleString("es-MX", { maximumFractionDigits: 2 });
/**
 * @param {number} budget
 * @param {number} burn
 */
export const etc = (budget, burn) => Math.round((budget - burn) * 100) / 100;
/**
 * @param {number} budget
 * @param {number} burn
 */
export const advance = (budget, burn) =>
  Math.round((burn / budget) * 1000) / 10;
/**
 * @param {{budget: string|number, burn: string|number}[]} rows
 */
export function averageCost(rows) {
  const values = rows
    .filter((row) => row.burn !== "")
    .map((row) =>
      Number(row.budget) > 0
        ? (Number(row.burn) / Number(row.budget)) * 100
        : null,
    )
    .filter((n) => n !== null && Number.isFinite(n));
  return values.length
    ? fmt(values.reduce((a, b) => a + b, 0) / values.length) + "%"
    : "—";
}
