// Comparaciones mensuales y frecuencia de cumplimiento sobre capturas guardadas.
export function previousMonth(month) {
  const [year, number] = month.split("-").map(Number);
  return number === 1
    ? `${year - 1}-12`
    : `${year}-${String(number - 1).padStart(2, "0")}`;
}

export function selectMonths(matrix, start, end) {
  const indices = matrix.headers
    .map((_, i) => i)
    .filter((i) => i >= start - 1 && i < end);
  return {
    ...matrix,
    headers: indices.map((i) => matrix.headers[i]),
    partial: indices.map((i) => matrix.partial?.[i]),
    rows: matrix.rows.map((row) => ({
      ...row,
      cells: indices.map((i) => row.cells[i]),
    })),
    totals: indices.map((i) => matrix.totals[i]),
  };
}

export function withComparison(summary, previous, matrix) {
  const ranks = matrix.rows
    .map((row) => {
      const cells = row.cells.filter(
        (cell) => cell && cell.total > 0 && Number.isFinite(cell.c),
      );
      return {
        name: row.name,
        observed: cells.length,
        good: cells.filter((cell) => cell.c === 100).length,
        low: cells.filter((cell) => cell.c >= 0 && cell.c <= 50).length,
      };
    })
    .filter((row) => row.observed > 0);
  const best = ranks
    .filter((row) => row.good > 0)
    .sort(
      (a, b) =>
        b.good - a.good ||
        b.good / b.observed - a.good / a.observed ||
        a.name.localeCompare(b.name),
    )[0];
  const worst = ranks
    .filter((row) => row.low > 0)
    .sort(
      (a, b) =>
        b.low - a.low ||
        b.low / b.observed - a.low / a.observed ||
        a.name.localeCompare(b.name),
    )[0];
  return {
    ...summary,
    previous: previous?.available === false ? null : previous?.totals,
    best: best
      ? {
          ...best,
          note: `100% C en ${best.good} de ${best.observed} meses con datos`,
        }
      : null,
    worst: worst
      ? {
          ...worst,
          note: `0–50% C en ${worst.low} de ${worst.observed} meses con datos`,
        }
      : null,
  };
}
