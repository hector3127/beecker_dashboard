import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  actionsModel,
  normalize,
  dateText,
  stateClass,
} from "../../frontend/static/scripts/pages/project_detail/sections/actions_model.js";

const frozen = JSON.parse(
  fs.readFileSync(new URL("./frozen/actions.json", import.meta.url), "utf8"),
);
const plain = (x) => JSON.parse(JSON.stringify(x));
test("Action dates, search and state colors match original helpers", () => {
  assert.equal(frozen.helpers.length, 17);
  for (const item of frozen.helpers) {
    assert.equal(normalize(item.input), item.normalize);
    assert.equal(dateText(item.input), item.date);
    assert.equal(stateClass(item.input), item.state);
  }
});
assert.equal(frozen.cases.length, 3);
for (const { name, dashboard, expected } of frozen.cases) {
  test(`Actions summary matches legacy (${name}) without mutating input`, () => {
    const input = structuredClone(dashboard);
    assert.deepEqual(plain(actionsModel(input, "2026-10-23")), expected);
    assert.deepEqual(input, dashboard);
  });
}
