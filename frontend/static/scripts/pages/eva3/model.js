// Numeric rules retained from the previous deferred-consumption script.
export const fmt = (n) =>
  Number(n).toLocaleString("es-MX", { maximumFractionDigits: 2 });
export const etc = (budget, burn) => Math.round((budget - burn) * 100) / 100;
export const advance = (budget, burn) =>
  Math.round((burn / budget) * 1000) / 10;
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
