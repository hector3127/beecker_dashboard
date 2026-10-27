import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  context,
  facts,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_ai_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/aer_ai_context.json", import.meta.url),
    "utf8",
  ),
);
const plain = (x) => JSON.parse(JSON.stringify(x));
assert.equal(frozen.length, 6);
for (const item of frozen) {
  test(`AER context and facts match original: ${item.label}/${!!item.state.accionesPartes}`, () => {
    const dashboard = structuredClone(item.dashboard),
      state = structuredClone(item.state);
    const now = new Date("2026-10-23T18:00:00Z");
    assert.deepEqual(plain(context(dashboard, state, now)), item.context);
    assert.deepEqual(plain(facts(dashboard, state, now)), item.facts);
    assert.deepEqual(dashboard, item.dashboard);
    assert.deepEqual(state, item.state);
  });
}
