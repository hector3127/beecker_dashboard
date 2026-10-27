import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { createProjectFeatureContexts } from "../../frontend/static/scripts/pages/project_detail/sections/project_feature_contexts.js";
import {
  createProjectState,
  bindProjectState,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
function setup() {
  const store = createProjectState(),
    calls = [];
  store.aer = { proyecto: { id: "P" } };
  store.ixs = { proyecto: { id: "P" } };
  store.aerAi.id = store.ixsAi.id = "P";
  const scope = {
    window: {
      beeAerAiSources: { bind: (value) => value },
      beeAerAiActions: { bind: (value) => value },
    },
    ixsClienteAccionesCache: store.clientCache,
  };
  bindProjectState(scope, store);
  for (const name of [
    "_aerRenderTab",
    "_aerToast",
    "_aerStartSaving",
    "showError",
    "aerIAContexto",
    "aerIAAbrirConfigMinutas",
    "aerIAPresentacionModular",
    "aerCambiarTab",
  ])
    scope[name] = (...args) => calls.push([name, ...args]);
  scope.aerAccionesModulares = () => ({ open: () => calls.push(["open"]) });
  vm.runInNewContext(source.match(/  function ixsCAActivo[^\n]+/)[0], scope);
  for (const name of [
    "aerRiesgosContexto",
    "aerAccionesContexto",
    "aerIAFuentesModulares",
    "aerIAPresentacionContexto",
    "aerIAAccionesModulares",
  ])
    vm.runInNewContext(
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
      scope,
    );
  return { store, scope, calls, contexts: createProjectFeatureContexts(store) };
}
const sameKeys = (a, b) =>
  assert.deepEqual(Object.keys(a).sort(), Object.keys(b).sort());

for (const family of ["aer", "ixs"])
  test(`${family}: Actions keeps shared cache, parts, inactive paint and snapshot rules`, (t) => {
    const { store, scope, contexts, calls } = setup();
    const before = globalThis.document;
    globalThis.document = scope.document = {
      querySelector: () => (family === "ixs" ? {} : null),
    };
    t.after(() => {
      globalThis.document = before;
    });
    store.aerTab = store.ixsTab = "acciones";
    store.clientCache.P = {};
    const old = scope.aerAccionesContexto();
    const next = contexts.actions({
      paint: old.paint,
      toast: old.toast,
      error: old.error,
    });
    sameKeys(next, old);
    assert.equal(next.family, old.family);
    const rows = { filas: [1] };
    old.actions(rows);
    const painted = calls.length;
    next.actions(rows);
    assert.equal(calls.length, painted * 2);
    old.loadingParts(true);
    assert.equal(next.partsLoading(), true);
    const parts = [{ uid: "part" }];
    next.setParts(parts);
    assert.equal(old.parts(), parts);
    assert.equal(
      store.clientCache.P.partes,
      family === "ixs" ? parts : undefined,
    );
    store.aerTab = store.ixsTab = "ia";
    assert.equal(next.active(), old.active());
    const count = calls.length;
    old.paintParts();
    const after = calls.length;
    next.paintParts();
    assert.equal(calls.length - after, after - count);
    const replacement = { filas: [] };
    next.storeActions(replacement);
    assert.equal(old.dashboard.acciones, replacement);
    store.aer = { proyecto: { id: "P" } };
    assert.equal(next.current(), old.current());
    assert.equal(next.current(), false);
  });

for (const [method, name, keys, tab] of [
  [
    "risks",
    "aerRiesgosContexto",
    ["paint", "saving", "error", "openAction"],
    "riesgos",
  ],
  [
    "aerSources",
    "aerIAFuentesModulares",
    ["paint", "context", "toast", "openConfig"],
    "ia",
  ],
  [
    "aerPresentation",
    "aerIAPresentacionContexto",
    ["paint", "toast", "actions"],
    "ia",
  ],
  [
    "aerActions",
    "aerIAAccionesModulares",
    ["paint", "toast", "error", "context", "presentation", "sources", "tab"],
    "ia",
  ],
])
  test(`${method}: contract and distinct refresh guards match previous`, () => {
    const { store, scope, contexts } = setup();
    store.aerTab = tab;
    const old = scope[name](),
      callbacks = Object.fromEntries(keys.map((key) => [key, old[key]]));
    const next = contexts[method](callbacks);
    sameKeys(next, old);
    assert.equal(next.state, old.state);
    assert.equal(next.dashboard, old.dashboard);
    assert.equal(next.current(), old.current());
    assert.equal(next.active(), old.active());
    for (const key of keys) assert.equal(next[key], old[key]);
    store.aerTab = "ejecutivo";
    assert.equal(next.active(), old.active());
    store.aer = { proyecto: { id: "P" } };
    assert.equal(next.current(), old.current());
    store.aerAi = { ...store.aerAi };
    assert.equal(next.current(), old.current());
    store.aer = { proyecto: { id: "OTHER" } };
    assert.equal(next.current(), old.current());
  });
test("IXS AI rejects another state or project exactly like the source guard", () => {
  const { store, scope, contexts } = setup();
  const expression = source.match(
    /current:window\.beeProjectFeatureContexts\?window\.beeProjectFeatureContexts\.ixsCurrent:state=>([^\n]+),/,
  )[1];
  const original = vm.runInNewContext(`state=>${expression}`, scope);
  const state = store.ixsAi;
  for (const value of [state, { ...state }, null])
    assert.equal(contexts.ixsCurrent(value), original(value));
  store.ixs = { proyecto: { id: "OTHER" } };
  assert.equal(contexts.ixsCurrent(state), original(state));
  store.ixs = null;
  assert.equal(contexts.ixsCurrent(state), original(state));
});
