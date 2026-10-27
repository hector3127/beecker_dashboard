import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  azureGroups,
  groupStatus,
  iterationStage,
  matchesPerson,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_azure_groups_model.js";

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/ixs_azure_groups.json", import.meta.url),
    "utf8",
  ),
);
const same = (a, b) => assert.equal(JSON.stringify(a), JSON.stringify(b));
test("group status and iteration preserve the original classifiers", () => {
  assert.equal(frozen.statuses.length, 13);
  assert.equal(frozen.stages.length, 5);
  for (const { input, expected } of frozen.statuses)
    assert.equal(groupStatus(input), expected);
  for (const { input, expected } of frozen.stages)
    assert.equal(
      iterationStage(input),
      expected.kind === "undefined" ? undefined : expected.value,
    );
});
test("people, iterations, stages and ordering match the original without changing inputs", () => {
  assert.equal(frozen.groups.length, 4);
  for (const { input, expected } of frozen.groups) {
    const state = structuredClone(input);
    same(azureGroups(state), expected);
    assert.deepEqual(state, input);
  }
});

test("person search keeps Spanish case matching and stage search without accent normalization", () => {
  const person = {
    persona: "Ana Pérez",
    iteraciones: [{ etapa: "Development" }],
  };
  assert.equal(matchesPerson(person, "  PÉREZ "), true);
  assert.equal(matchesPerson(person, "development"), true);
  assert.equal(matchesPerson(person, "perez"), false);
  assert.equal(matchesPerson(person, ""), true);
  assert.equal(matchesPerson(person, "other"), false);
});
