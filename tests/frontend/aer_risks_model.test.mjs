import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  dedupRisks,
  risksModel,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_risks_model.js";
const frozen = JSON.parse(
  fs.readFileSync(new URL("./frozen/aer_risks.json", import.meta.url), "utf8"),
);
const plain = (value) => JSON.parse(JSON.stringify(value));

assert.equal(frozen.summaries.length, 4);
assert.equal(frozen.dedup.length, 4);
for (const { name, dashboard, expected, percentages } of frozen.summaries) {
  test(`Risk summary matches original: ${name}`, () => {
    const before = plain(dashboard);
    const actual = risksModel(dashboard, new Date(frozen.now));
    assert.deepEqual(plain(actual), expected);
    assert.equal(percentages.length, 25);
    for (const { impacto, probabilidad, expected: percentage } of percentages)
      assert.equal(actual.riesgoPct({ impacto, probabilidad }), percentage);
    assert.deepEqual(dashboard, before);
  });
}
for (const { input, expected } of frozen.dedup) {
  test(`Risk deduplication preserves original merging and ordering (${JSON.stringify(input)})`, () => {
    const before = plain(input);
    assert.deepEqual(plain(dedupRisks(input)), expected);
    assert.deepEqual(input, before);
  });
}
test("Existing title grouping retains the first row even with distinct owners and dates", () => {
  assert.deepEqual(
    dedupRisks(frozen.firstOwner.input),
    frozen.firstOwner.expected,
  );
});
