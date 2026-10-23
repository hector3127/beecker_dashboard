import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  azureGroups,
  groupStatus,
  iterationStage,
  matchesPerson,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_azure_groups_model.js";

const code = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const pick = (name) =>
  code.match(new RegExp(String.raw`  function ${name}\([\s\S]*?\n  \}`))[0];
const legacy = { ixsAzureState: {} };
vm.runInNewContext(
  ["_ixsAz84Status", "_ixsAz84Stage", "_ixsAz84GroupData"].map(pick).join("\n"),
  legacy,
);
const same = (a, b) => assert.equal(JSON.stringify(a), JSON.stringify(b));

test("group status and iteration preserve the original classifiers", () => {
  for (const state of [
    " Active ",
    "In progress",
    "blocked",
    "CANCELLED",
    "Closed",
    "Not applicable",
    "Completed",
    "Inactive",
    "Rejected",
    "Proposed",
    "Risk",
    "",
    null,
  ]) {
    assert.equal(groupStatus(state), legacy._ixsAz84Status(state));
  }
  for (const path of ["A\\Dev", "A\\QA\\", " ", "\\", null])
    assert.equal(iterationStage(path), legacy._ixsAz84Stage(path));
});

test("people, iterations, stages and ordering match the original without changing inputs", () => {
  const allItems = [
    "Active",
    "Closed",
    "Cancelled",
    "Blocked",
    "Proposed",
    "In progress",
    "Rejected",
    "Completed",
    "",
  ].map((estado, i) => ({
    id: i,
    estado,
    asignadoA: ["Ana", " Luis ", "", "Ana"][i % 4],
    iterationPath: ["A\\Dev", "B\\Dev", "A\\QA", ""][i % 4],
  }));
  for (const state of [
    { allItems },
    { allItems: [] },
    {},
    { allItems: "invalid" },
  ]) {
    const before = JSON.stringify(state);
    legacy.ixsAzureState = state;
    same(azureGroups(state), legacy._ixsAz84GroupData());
    assert.equal(JSON.stringify(state), before);
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
