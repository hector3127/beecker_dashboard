import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  isSummaryQuestion,
  summaryPayload,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_ai_actions_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/aer_ai_actions_model.json", import.meta.url),
    "utf8",
  ),
);
assert.equal(frozen.questions.length, 6);
assert.equal(frozen.payloads.length, 3);
for (const { input, expected } of frozen.questions)
  test(`Question routing retains original decision: ${input}`, () =>
    assert.equal(isSummaryQuestion(input), expected));
test("Summary context preserves five selected files and exact instructions", () => {
  for (const { input, expected } of frozen.payloads) {
    const state = structuredClone(input);
    assert.deepEqual(summaryPayload(state, expected.instrucciones), expected);
    assert.deepEqual(state, input);
  }
});
