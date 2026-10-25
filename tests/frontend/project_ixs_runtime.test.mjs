import test from "node:test";
import assert from "node:assert/strict";
import { createIxsRuntime } from "../../frontend/static/scripts/pages/project_detail/sections/project_ixs_runtime.js";
import { createProjectState } from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";
import { createProjectContexts } from "../../frontend/static/scripts/pages/project_detail/sections/project_contexts.js";

function setup(t) {
  const store = createProjectState(),
    calls = [];
  store.ixs = { proyecto: { id: "P" } };
  const target = { id: "dashboard-proyecto-detalle" },
    before = globalThis.document;
  globalThis.document = {
    getElementById: () => target,
    querySelector: () => ({}),
  };
  t.after(() => {
    globalThis.document = before;
  });
  const services = {
    tools: {
      styles: {},
      editPlanning: (...args) => calls.push(["editor", ...args]),
      communique: () => calls.push(["communique"]),
    },
    contexts: createProjectContexts(store),
    entry: { serverError() {} },
    shell: {
      mount: (root, env) => calls.push(["mount", root, env]),
      bind: (env) => ({
        select: (tab) => {
          env.tab(tab);
          env.render();
        },
        refresh: () => env.apply({ proyecto: { id: "P" } }, "ia"),
      }),
    },
    tabs: {
      ixs: (env) => calls.push(["dispatch", env]),
      aer: (env) => calls.push(["shared", env]),
    },
    session: {
      ixs: (data, env) => {
        store.ixs = data;
        store.ixsTab = "resumen";
        env.render.ixs();
      },
      ai: (env) => {
        env.render.ai();
        env.aiLoads.sources();
        env.aiLoads.history();
        env.aiLoads.drive();
      },
      clientActions: (env) => {
        calls.push(["client", env.cache]);
        env.render.aerTab();
      },
    },
    adapters: {
      support: (reload) => ({ project: () => store.ixs, reload }),
      load: (name, paint) => calls.push(["load", name, paint]),
      paint: (env) => calls.push(["paint", env]),
      actions: (env) => env,
    },
    support: {
      resources: (env) => calls.push(["resources", env]),
      editMilestone: (index, env) => calls.push(["marker", index, env]),
    },
  };
  const callbacks = {
    aerTabs: () => ({ selectAer() {}, aerContexts: {} }),
    reload() {},
    createRaid() {},
    manualRaid() {},
    previous() {},
  };
  return {
    store,
    calls,
    services,
    callbacks,
    target,
    runtime: createIxsRuntime(store, services).connect(callbacks),
  };
}
test("mount and tab actions use modules and preserve lazy state/editor bindings", (t) => {
  const { store, calls, target, runtime, callbacks } = setup(t);
  runtime.mount();
  assert.equal(calls[0][1], target);
  assert.equal(calls[0][2].project, store.ixs);
  runtime.dispatch();
  const env = calls.at(-1)[1];
  assert.equal(env.ixsStates().planning, store.ixsPlanning);
  env.resources();
  assert.equal(calls.at(-1)[1].reload, callbacks.reload);
  env.planningActions.editMarker(7);
  assert.equal(calls.at(-1)[1], 7);
  env.planningActions.edit("compromiso", "hito/'1", "Hito");
  assert.deepEqual(calls.at(-1), [
    "editor",
    "compromiso",
    "hito%2F%271",
    "Hito",
  ]);
  env.planningActions.extension();
  assert.deepEqual(calls.at(-1), ["communique"]);
  env.planningActions.azure();
  assert.equal(store.ixsTab, "azure");
  assert.equal(calls.at(-1)[0], "mount");
});
test("AI rendering/loading and shared client actions stay inside the runtime", (t) => {
  const { calls, store, runtime, callbacks } = setup(t);
  runtime.openAi();
  assert.deepEqual(
    calls
      .map((x) => x.slice(0, 2))
      .map((x) => (x[0] === "load" ? x : x.slice(0, 1))),
    [["paint"], ["load", "sources"], ["load", "history"], ["load", "drive"]],
  );
  const action = runtime.aiActions();
  assert.equal(action.raidOpen, callbacks.createRaid);
  action.tab("recursos");
  assert.equal(store.ixsTab, "recursos");
  runtime.loadClientActions();
  assert.equal(calls.at(-2)[1], store.clientCache);
  assert.equal(calls.at(-1)[0], "shared");
});
test("refresh invalidates shared cache and initializes back to executive", (t) => {
  const { calls, store, runtime } = setup(t);
  store.clientCache.P = { cached: true };
  store.ixsTab = "ia";
  runtime.refresh();
  assert.equal(store.clientCache.P, undefined);
  assert.equal(store.ixsTab, "resumen");
  assert.equal(calls.at(-1)[0], "mount");
});
