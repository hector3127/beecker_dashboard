import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { groupStatus } from "../../frontend/static/scripts/pages/project_detail/sections/ixs_azure_groups_model.js";

const captured = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/ixs_azure_summary.json", import.meta.url),
    "utf8",
  ),
);
// Evaluate the current pure classifier without loading its DOM-only imports.
const classifier = fs
  .readFileSync(
    "frontend/static/scripts/pages/project_detail/sections/ixs_planning_azure.js",
    "utf8",
  )
  .match(/export function statusClass\([\s\S]*?\n}/)[0]
  .replace("export ", "");
const context = { groupStatus };
vm.runInNewContext(classifier, context);
vm.runInNewContext(
  fs
    .readFileSync(
      "frontend/static/scripts/pages/project_detail/sections/ixs_azure_summary_model.js",
      "utf8",
    )
    .replace(/^import.*;$/gm, "")
    .replaceAll("export ", ""),
  context,
);

for (const { name, state, expected } of captured.cases) {
  test(`summary equals original figures, distribution, ordering and dates: ${name}`, () => {
    const before = JSON.stringify(state);
    const actual = context.azureSummary(state);
    for (const field of captured.fields) {
      assert.equal(
        JSON.stringify(actual[field]),
        JSON.stringify(expected[field]),
        field,
      );
    }
    assert.equal(JSON.stringify(state), before);
    assert.equal(
      actual.staleSorted.length,
      Math.min(8, (state.stale || []).length),
    );
  });
}

test("attention keeps top eight and average is not clamped by the model", () => {
  const state = {
    items: [{ avanceTotal: 150 }, { avanceTotal: -10 }],
    stale: Array.from({ length: 12 }, (_, i) => ({
      id: i,
      diasSinActualizar: i,
    })),
  };
  const value = context.azureSummary(state);
  assert.equal(value.avg, 70);
  assert.equal(value.staleCount, 12);
  assert.equal(value.staleSorted.length, 8);
  assert.equal(value.staleSorted[0].diasSinActualizar, 11);
});
