import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createProjectFeatureContexts } from "../../frontend/static/scripts/pages/project_detail/sections/project_feature_contexts.js";
import { createProjectState } from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/project_feature_contexts.json", import.meta.url),
    "utf8",
  ),
);
function callbacksFrom(value, calls) {
  const registry = new Map();
  function restore(node) {
    if (node && node.$callback) {
      if (!registry.has(node.$callback))
        registry.set(node.$callback, (...args) =>
          calls.push([node.$callback, ...args]),
        );
      return registry.get(node.$callback);
    }
    if (Array.isArray(node)) return node.map(restore);
    if (node && typeof node === "object")
      return Object.fromEntries(
        Object.entries(node).map(([key, item]) => [key, restore(item)]),
      );
    return node;
  }
  return restore(value);
}
function setup() {
  const store = createProjectState();
  store.aer = { proyecto: { id: "P" } };
  store.ixs = { proyecto: { id: "P" } };
  store.aerAi.id = store.ixsAi.id = "P";
  return { store, contexts: createProjectFeatureContexts(store) };
}
for (const entry of frozen.actions) {
  const { family } = entry;
  test(`${family}: Actions keeps shared cache, parts, inactive paint and snapshot rules`, (t) => {
    const { store, contexts } = setup(),
      calls = [],
      previous = globalThis.document;
    globalThis.document = {
      querySelector: () => (family === "ixs" ? {} : null),
    };
    t.after(() => {
      globalThis.document = previous;
    });
    store.aerTab = store.ixsTab = "acciones";
    store.clientCache.P = {};
    const next = contexts.actions(callbacksFrom(entry.callbacks, calls));
    assert.deepEqual(Object.keys(next).sort(), entry.keys);
    assert.equal(next.family, entry.observedFamily);
    const rows = { filas: [1] };
    next.actions(rows);
    assert.equal(calls.length, entry.paints);
    assert.equal(next.dashboard.acciones === rows, entry.sameActions);
    next.loadingParts(true);
    assert.equal(next.partsLoading(), entry.partsLoading);
    const parts = [{ uid: "part" }];
    next.setParts(parts);
    assert.equal(next.parts() === parts, entry.sameParts);
    assert.equal(store.clientCache.P.partes === parts, entry.cacheSame);
    store.aerTab = store.ixsTab = "ia";
    assert.equal(next.active(), entry.inactive);
    const count = calls.length;
    next.paintParts();
    assert.equal(calls.length - count, entry.partsPaints);
    const replacement = { filas: [] };
    next.storeActions(replacement);
    assert.equal(next.dashboard.acciones === replacement, entry.stored);
    store.aer = { proyecto: { id: "P" } };
    assert.equal(next.current(), entry.replaced);
    assert.equal(next.current(), false);
  });
}
for (const entry of frozen.contracts) {
  const { method, tab } = entry;
  test(`${method}: contract and distinct refresh guards match previous`, () => {
    const { store, contexts } = setup();
    store.aerTab = tab;
    const callbacks = callbacksFrom(entry.callbacks, []),
      next = contexts[method](callbacks);
    assert.deepEqual(Object.keys(next).sort(), entry.keys);
    assert.equal(next.state === store.aerAi, entry.sameState);
    assert.equal(next.dashboard === store.aer, entry.sameDashboard);
    for (const [key, value] of Object.entries(callbacks))
      assert.equal(next[key], value);
    const guards = [next.current()];
    assert.equal(next.active(), entry.active);
    store.aerTab = "ejecutivo";
    assert.equal(next.active(), entry.inactive);
    store.aer = { proyecto: { id: "P" } };
    guards.push(next.current());
    store.aerAi = { ...store.aerAi };
    guards.push(next.current());
    store.aer = { proyecto: { id: "OTHER" } };
    guards.push(next.current());
    assert.deepEqual(guards, entry.guards);
  });
}
test("IXS AI rejects another state or project exactly like the source guard", () => {
  const { store, contexts } = setup(),
    state = store.ixsAi,
    observed = [
      contexts.ixsCurrent(state),
      contexts.ixsCurrent({ ...state }),
      contexts.ixsCurrent(null),
    ];
  store.ixs = { proyecto: { id: "OTHER" } };
  observed.push(contexts.ixsCurrent(state));
  store.ixs = null;
  observed.push(contexts.ixsCurrent(state));
  assert.deepEqual(observed, frozen.ixsGuards);
});
