import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  stage,
  aerStatus,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_shell_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/project_shell.json", import.meta.url),
    "utf8",
  ),
);
const now = "2026-10-23T18:00:00Z";
assert.equal(frozen.stages.length, 8);
for (const { label, data, expected } of frozen.stages) {
  test(`Header stage matches original: ${label}`, () => {
    const input = structuredClone(data);
    assert.deepEqual(stage(input, new Date(now)), expected);
    assert.deepEqual(input, data);
  });
}
test("AER badge preserves original classification and defaults", () => {
  assert.equal(frozen.statuses.length, 11);
  for (const { input, expected } of frozen.statuses)
    assert.equal(aerStatus(input), expected);
});
