import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  memoryDate,
  summaryMarkup,
  minuteSummary,
  presentation,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_ai_presentation_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/aer_ai_presentation.json", import.meta.url),
    "utf8",
  ),
);
const now = new Date("2026-10-23T18:00:00Z");
const plain = (x) => JSON.parse(JSON.stringify(x));
assert.equal(frozen.minutes.length, 5);
for (const { input, expected } of frozen.minutes)
  test(`Minute excerpt matches original (${input.slice(0, 35)})`, () =>
    assert.equal(minuteSummary(input), expected));
test("Memory timestamps preserve Apps Script wall time without conversion", () => {
  assert.equal(frozen.stamps.length, 5);
  for (const { input, expected } of frozen.stamps)
    assert.equal(memoryDate(input), expected);
});
assert.equal(frozen.markup.length, 6);
for (const { input, expected } of frozen.markup)
  test(`Minimal summary markup retains original escaping (${input.slice(0, 25)})`, () =>
    assert.equal(summaryMarkup(input), expected));
assert.equal(frozen.cases.length, 8);
for (const item of frozen.cases) {
  const { dashboard, state, expected } = item;
  test(`Presentation matches original (${dashboard.kpis.consumoPct}/${!!state.analisis})`, () => {
    const d = structuredClone(dashboard),
      s = structuredClone(state);
    assert.deepEqual(plain(presentation(d, s, now)), expected);
    assert.deepEqual(d, dashboard);
    assert.deepEqual(s, state);
  });
}
