import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  emptyFilters,
  initialRange,
  rowMatches,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_planning_filters_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/aer_planning_filters.json", import.meta.url),
    "utf8",
  ),
);
assert.equal(frozen.rows.length, 3);
assert.equal(frozen.filters.length, 12);
assert.equal(frozen.ranges.length, 4);
for (const { patch, expected } of frozen.filters) {
  test(`Filters retain original row matching ${JSON.stringify(patch)}`, () => {
    const rows = structuredClone(frozen.rows);
    const filters = { ...emptyFilters(), ...patch };
    assert.deepEqual(
      rows.map((row) => rowMatches(row, filters)),
      expected,
    );
    assert.deepEqual(rows, frozen.rows);
  });
}
test("Range initialization matches original and retains both chosen months", () => {
  for (const { input, expected } of frozen.ranges) {
    const range = structuredClone(input);
    assert.deepEqual(
      initialRange(range, new Date("2026-10-24T18:00:00Z")),
      expected,
    );
    assert.deepEqual(range, input);
  }
});
