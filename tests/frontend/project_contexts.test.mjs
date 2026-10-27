import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createProjectContexts } from "../../frontend/static/scripts/pages/project_detail/sections/project_contexts.js";
import { createProjectState } from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/project_contexts.json", import.meta.url),
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
  store.aer = { proyecto: { id: "AER" } };
  store.ixs = { proyecto: { id: "IXS" } };
  return { store, contexts: createProjectContexts(store) };
}
function keys(actual, expected) {
  assert.deepEqual(Object.keys(actual).sort(), expected);
}
test("entry contract keeps metadata references, callbacks and invalidation", () => {
  const { store, contexts } = setup(),
    entry = frozen.entry,
    callbacks = callbacksFrom(entry.callbacks, []),
    next = contexts.entry(callbacks);
  keys(next, entry.keys);
  for (const [key, value] of Object.entries(callbacks))
    assert.equal(next[key], value);
  const metadata = { P: { servicio: "IXB" } };
  store.metadata = metadata;
  assert.equal(next.metadata() === metadata, entry.sameMetadata);
  next.metadata({});
  assert.equal(next.metadata(), store.metadata);
  assert.deepEqual(next.metadata(), entry.metadata);
  next.invalidatePrevious();
  next.invalidatePrevious();
  assert.equal(store.request, entry.request);
});
test("session contract exposes the same mutable cells and cache", () => {
  const { store, contexts } = setup(),
    entry = frozen.session,
    callbacks = callbacksFrom(entry.callbacks, []),
    next = contexts.session(callbacks);
  keys(next, entry.keys);
  for (const [key, value] of Object.entries(callbacks))
    assert.equal(next[key], value);
  for (const { key, same, cleared } of entry.cells) {
    const value = { key };
    store[key] = value;
    assert.equal(next[key]() === value, same);
    next[key](value);
    assert.equal(
      store[key] === value,
      same,
      `${key}: setters preserve identity`,
    );
    next[key](null);
    assert.equal(store[key], cleared);
    assert.equal(next[key](), cleared);
  }
  next.globalId("P");
  assert.equal(store.projectId, entry.first);
  next.globalId("Q");
  assert.equal(store.projectId, entry.second);
  assert.equal(next.cache === store.clientCache, entry.cacheSame);
});
for (const entry of frozen.shells) {
  const { family } = entry;
  test(`${family}: shell snapshot, refresh and lifecycle match previous`, (t) => {
    const { store, contexts } = setup(),
      calls = [];
    let present = true;
    const previousDocument = globalThis.document;
    globalThis.document = { querySelector: () => (present ? {} : null) };
    t.after(() => {
      globalThis.document = previousDocument;
    });
    const callbacks = callbacksFrom(entry.callbacks, calls),
      next = contexts.shell(family, callbacks);
    keys(next, entry.keys);
    assert.equal(next.project, store[family]);
    assert.deepEqual(next.project, entry.project);
    assert.equal(next.current(), entry.current);
    present = false;
    assert.equal(next.current(), entry.absent);
    present = true;
    next.tab("planeacion");
    assert.equal(store[family === "aer" ? "aerTab" : "ixsTab"], entry.firstTab);
    store[family === "aer" ? "aerTab" : "ixsTab"] = "ia";
    assert.equal(next.tab(), entry.secondTab);
    store.clientCache.IXS = { cached: true };
    const result = { proyecto: { id: "updated" } };
    next.apply(result, "recursos");
    assert.deepEqual(
      {
        calls,
        state: store[family],
        tab: store[family === "aer" ? "aerTab" : "ixsTab"],
        cache: store.clientCache,
      },
      entry.applied,
    );
    if (family === "aer") {
      assert.equal(store.aer, result);
      assert.equal(store.aerTab, "recursos");
    } else assert.equal(store.clientCache.IXS, undefined);
    store[family] = null;
    assert.equal(next.current(), entry.replaced);
  });
}
test("tabs preserve lazy panel states, Azure synchronization and encoded editor IDs", () => {
  const { store, contexts } = setup(),
    entry = frozen.tabs,
    calls = [],
    callbacks = callbacksFrom(entry.callbacks, calls),
    next = contexts.tabs(callbacks);
  keys(next, entry.keys);
  keys(next.planningActions, entry.actionKeys);
  assert.equal(next.aerContexts, callbacks.aerContexts);
  assert.equal(next.planningActions.editMarker, callbacks.editMarker);
  assert.equal(next.planningActions.extension, callbacks.extension);
  const azure = { items: [] };
  next.syncAzure(azure);
  assert.equal(next.ixsStates().azure === azure, entry.sameAzure);
  next.syncPlanningAzure("P", [1]);
  assert.deepEqual(store.ixsAzure, entry.synced);
  assert.equal(next.ixsStates().azure.items[0], 1);
  store.ixsPlanning = { fresh: true };
  assert.equal(
    next.ixsStates().planning === store.ixsPlanning,
    entry.samePlanning,
  );
  next.planningActions.edit("Hito", "Á' /&", { fecha: "2026-10-23" });
  next.planningActions.azure();
  assert.deepEqual(calls, entry.calls);
});
