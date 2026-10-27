import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createProjectPanels } from "../../frontend/static/scripts/pages/project_detail/sections/project_panels.js";
import { createProjectState } from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/project_panels.json", import.meta.url),
    "utf8",
  ),
);

assert.equal(frozen.defaults.length, 7);
assert.equal(frozen.contracts.length, 3);
for (const { name, key, expected } of frozen.defaults) {
  test(`${name}: panel defaults match previous and instances stay independent`, () => {
    const a = createProjectState(),
      b = createProjectState();
    assert.deepEqual(a[key], expected);
    if (a[key] && typeof a[key] === "object") {
      assert.notEqual(a[key], b[key]);
      for (const field of Object.keys(a[key]))
        if (Array.isArray(a[key][field]))
          assert.notEqual(a[key][field], b[key][field]);
    }
  });
}
for (const entry of frozen.contracts) {
  const { method, tab } = entry;
  test(`${method}: context contract and lifecycle match previous`, () => {
    const store = createProjectState();
    store.aer = structuredClone(entry.dashboard);
    store.aerTab = tab;
    const noop = () => {};
    const callbacks = Object.fromEntries(
      entry.callbacks.map(({ key }) => [key, noop]),
    );
    const current = createProjectPanels(store)[method](callbacks);
    assert.deepEqual(Object.keys(current).sort(), entry.keys);
    assert.equal(current.dashboard, store.aer);
    assert.deepEqual(current.dashboard, entry.dashboard);
    assert.equal(current.id, entry.id);
    assert.equal(current.current(), entry.current);
    assert.equal(current.active(), entry.active);
    for (const { key, same } of entry.callbacks)
      assert.equal(current[key] === callbacks[key], same);
    if (method === "planning") {
      const range = structuredClone(entry.update.range),
        filters = structuredClone(entry.update.filters);
      current.setRange(range);
      current.setFilters(filters);
      assert.deepEqual(current.range(), entry.update.range);
      assert.deepEqual(current.filters(), entry.update.filters);
      assert.equal(current.range() === range, entry.update.sameRange);
      assert.equal(current.filters() === filters, entry.update.sameFilters);
    } else if (method === "effort") {
      const records = structuredClone(entry.update.records);
      current.setState(records);
      assert.deepEqual(current.state(), entry.update.records);
      assert.equal(current.state() === records, entry.update.same);
    } else {
      current.selected(entry.update.selected);
      assert.equal(current.selected(), entry.update.selected);
    }
    store.aerTab = "ia";
    assert.equal(current.active(), entry.inactive);
    store.aer = { proyecto: { id: "OTHER" } };
    assert.equal(current.current(), entry.replaced);
    assert.equal(current.current(), false);
  });
}
