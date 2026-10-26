import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  date,
  matches,
  csv,
} from "../../frontend/static/scripts/pages/eva1/model.js";
import { averageCost } from "../../frontend/static/scripts/pages/eva3/model.js";

// Outputs captured from the original inline scripts before their removal.
const reference = JSON.parse(
  fs.readFileSync(
    new URL("./snapshots/eva_models.json", import.meta.url),
    "utf8",
  ),
);

test("EVA1 filters and CSV match the captured previous inline script", async () => {
  assert.equal(reference.filters.length, 4);
  assert.equal(reference.dates.length, 4);
  for (const { rows, filters, visible, csv: expected } of reference.filters) {
    const selected = rows.filter((row) => matches(row.dataset, filters));
    assert.deepEqual(
      rows.map((row) => matches(row.dataset, filters)),
      visible,
    );
    const exported = new Blob([
      "\ufeff" +
        csv(selected.map((row) => row.cells.map((c) => c.innerText.trim()))),
    ]);
    assert.equal(await exported.text(), expected);
  }
  for (const { value, expected } of reference.dates)
    assert.equal(date(value), expected);
});

test("EVA3 average keeps pending rows and zero budgets out like the previous screen", () => {
  assert.equal(reference.costs.length, 3);
  for (const { rows, expected } of reference.costs)
    assert.equal(averageCost(rows), expected);
});
