import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  resourcesModel,
  resourceEditorSource,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_resources_model.js";

const captured = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/ixs_resources.json", import.meta.url),
    "utf8",
  ),
);
const json = (value) => JSON.parse(JSON.stringify(value));
const plain = (model) => json({ ...model, hours: [...model.hours] });

test("resources preserve normalization, overrides, duplicate hours and alerts", () => {
  for (const { data, state, expected } of captured.models) {
    const before = JSON.stringify([data, state]);
    assert.deepEqual(plain(resourcesModel(data, state)), expected);
    assert.equal(JSON.stringify([data, state]), before);
  }
  const { data, state } = captured.models[2];
  const model = resourcesModel(data, state);
  assert.equal(model.hours.get("ana perez").horas, 16);
  assert.equal(model.inactive.length, 1);
  assert.equal(model.missing.length, 1);
});

test("editor source keeps assignment-first fallback and exact names", () => {
  for (const { data, state, name, expected } of captured.editors) {
    const before = JSON.stringify([data, state]);
    assert.deepEqual(json(resourceEditorSource(data, state, name)), expected);
    assert.equal(JSON.stringify([data, state]), before);
  }
});
