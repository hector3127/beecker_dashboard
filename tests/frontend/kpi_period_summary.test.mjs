import assert from "node:assert/strict";
import test from "node:test";
import {
  previousMonth,
  selectMonths,
  withComparison,
} from "../../frontend/static/scripts/pages/kpis_dm/sections/period_summary.js";

test("el rango y las rachas conservan las capturas y distinguen cero de ausencia", () => {
  const matrix = {
    headers: ["Ene", "Feb", "Mar", "Abr"],
    totals: [null, null, null, null],
    rows: [
      {
        name: "Ana",
        cells: [
          { c: 100, total: 2 },
          null,
          { c: 100, total: 1 },
          { c: 0, total: 1 },
        ],
      },
      {
        name: "Luis",
        cells: [{ c: 50, total: 1 }, { c: 0, total: 2 }, null, null],
      },
    ],
  };
  const selected = selectMonths(matrix, 1, 3);
  const summary = withComparison({}, { available: false }, selected);
  assert.equal(summary.best.name, "Ana");
  assert.equal(summary.best.observed, 2);
  assert.equal(summary.worst.low, 2);
  assert.equal(summary.previous, null);
  assert.equal(matrix.headers.length, 4);
  assert.equal(previousMonth("2026-01"), "2025-12");
});
