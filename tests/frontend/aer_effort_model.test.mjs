import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  effortModel,
  weekRange,
  initialState,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_effort_model.js";

const frozen = JSON.parse(
  fs.readFileSync(new URL("./frozen/aer_effort.json", import.meta.url), "utf8"),
);
const plain = (x) => JSON.parse(JSON.stringify(x));
assert.equal(frozen.length, 12);
for (const item of frozen) {
  const { name, state } = item;
  test(`Effort summary, preview and range match original (${name}, ${state.registros?.length ?? "base"}, ${state.desde})`, () => {
    const dashboard = structuredClone(item.dashboard),
      inputState = structuredClone(state);
    const { state: actualState, ...actual } = effortModel(
      dashboard,
      inputState,
      new Date("2026-10-23T18:00:00Z"),
    );
    assert.deepEqual(plain(actual), item.expected);
    assert.deepEqual(plain(actualState), item.expectedState);
    assert.deepEqual(dashboard, item.dashboard);
    assert.deepEqual(inputState, state);
  });
}

test("Default range retains Monday through Sunday and chosen dates", () => {
  for (const now of [
    "2026-10-19T18:00:00Z",
    "2026-10-23T18:00:00Z",
    "2026-10-25T18:00:00Z",
  ])
    assert.deepEqual(weekRange(new Date(now)), {
      desde: "2026-10-19",
      hasta: "2026-10-25",
    });
  assert.deepEqual(initialState({ desde: "2026-01-01", hasta: "2026-12-31" }), {
    desde: "2026-01-01",
    hasta: "2026-12-31",
  });
});
