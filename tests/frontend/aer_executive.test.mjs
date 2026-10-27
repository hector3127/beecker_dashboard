import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  executiveModel,
  dimensions,
  hours,
  formatDate,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_executive_model.js";

// Salidas del original congeladas en frozen/aer_executive.json.
const frozen = JSON.parse(
  fs.readFileSync("tests/frontend/frozen/aer_executive.json", "utf8"),
);
const date = new Date("2026-10-23T18:00:00Z");
const json = (value) => JSON.parse(JSON.stringify(value));

test("AER executive presentation keeps all original thresholds, fallbacks and ordering", () => {
  assert.equal(frozen.view.length, 27);
  for (const { input, expected } of frozen.view) {
    const data = structuredClone(input);
    assert.deepEqual(json(executiveModel(data, date)), expected);
    assert.deepEqual(data, input, "the model must not mutate its input");
  }
});

test("dimensions and formatting retain zero, missing sources and rounding", () => {
  for (const { input, expected } of frozen.formats.hours) {
    assert.equal(hours(input === "__undefined__" ? undefined : input), expected);
  }
  for (const { input, expected } of frozen.formats.dates) {
    assert.equal(formatDate(input), expected);
  }
  for (const { input, expected } of frozen.formats.dimensions) {
    assert.deepEqual(json(dimensions(input)), expected);
  }
});
