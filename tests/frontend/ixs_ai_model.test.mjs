import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import * as modern from "../../frontend/static/scripts/pages/project_detail/sections/ixs_ai_model.js";
const frozen = JSON.parse(
  fs.readFileSync(new URL("./frozen/ixs_ai.json", import.meta.url), "utf8"),
);
const plain = (value) => JSON.parse(JSON.stringify(value));

function compare(entry) {
  const { state, project, milestones, expected } = entry;
  const before = plain({ state, project, milestones });
  const context = modern.context(state, project, milestones);
  const snapshot = modern.snapshot(state, context);
  assert.deepEqual(plain(context), expected.context);
  assert.deepEqual(plain(snapshot), expected.snapshot);
  assert.deepEqual(
    plain(modern.changes(state, () => snapshot)),
    expected.changes,
  );
  assert.deepEqual(plain(modern.capacity(state)), expected.capacity);
  assert.deepEqual({ state, project, milestones }, before);
  return { context, snapshot };
}
test("IA preserves original context, snapshots, changes and capacity with full data", () => {
  assert.equal(frozen.cases.length, 4);
  const { context, snapshot } = compare(frozen.cases[0]);
  assert.equal(context.minutas.length, 3);
  assert.equal(context.minutas[0].contenido.length, 1200);
  // Original context and snapshot deliberately include different durations.
  assert.equal(context.horasClockifyTotal, 9.35);
  assert.equal(snapshot.horas, 10.35);
});
test("IA preserves empty sources and no previous snapshot", () =>
  compare(frozen.cases[1]));
test("IA preserves incomplete comparisons and partial source availability", () => {
  compare(frozen.cases[2]);
  compare(frozen.cases[3]);
});
test("IA keeps the previous lazy snapshot behavior when no memory exists", () => {
  assert.equal(
    modern.changes({}, () => {
      throw Error("unexpected snapshot");
    }),
    null,
  );
});
