import test from "node:test";
import assert from "node:assert/strict";
import { createAerRuntime } from "../../frontend/static/scripts/pages/project_detail/sections/project_aer_runtime.js";
import { createProjectState } from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";
import { createProjectContexts } from "../../frontend/static/scripts/pages/project_detail/sections/project_contexts.js";
import { createProjectPanels } from "../../frontend/static/scripts/pages/project_detail/sections/project_panels.js";
import { createProjectFeatureContexts } from "../../frontend/static/scripts/pages/project_detail/sections/project_feature_contexts.js";

function setup(t) {
  const store = createProjectState(),
    calls = [];
  store.aer = { proyecto: { id: "P", nombre: "Proyecto" } };
  store.aerAi.id = "P";
  let ixs = false;
  const before = globalThis.document,
    target = {};
  globalThis.document = {
    getElementById: () => target,
    querySelector: (selector) =>
      selector.endsWith(".ixs-shell") ? (ixs ? {} : null) : {},
  };
  t.after(() => {
    globalThis.document = before;
  });
  const methods = (names) =>
    Object.fromEntries(
      names.map((name) => [name, (...args) => calls.push([name, ...args])]),
    );
  const actions = methods([
    "analyze",
    "generateSummary",
    "generateMail",
    "generateMinute",
    "saveMinute",
    "copyMinute",
    "copySavedMinute",
    "copySummary",
    "saveConfig",
    "resetPrompt",
    "ask",
  ]);
  const services = {
    contexts: createProjectContexts(store),
    panels: createProjectPanels(store),
    features: createProjectFeatureContexts(store),
    feedback: { toast() {}, saving() {} },
    entry: { serverError() {} },
    selectIxs: (tab) => calls.push(["ixs-tab", tab]),
    views: {
      beeAerAiModel: { context: () => ({ id: store.aer.proyecto.id }) },
      beeProjectActions: {
        bind: () => ({
          loadParts: (force) => calls.push(["parts", force]),
          open: () => calls.push(["action"]),
        }),
      },
      beeAerRisks: { bind: () => ({ open: () => calls.push(["risk"]) }) },
      beeAerAiSources: {
        bind: () =>
          methods(["analysis", "minutes", "config", "summary", "files"]),
      },
      beeAerAiActions: {
        bind: (env) => {
          calls.push(["bind-ai", env]);
          return actions;
        },
      },
      beeAerAiPresentation: {
        bind: (env) => ({ config: () => calls.push(["config-view", env]) }),
      },
      beeProjectCommunique: {
        open: (value) => calls.push(["communique", value]),
      },
    },
    session: {
      aer: (data, env) => {
        store.aer = data;
        store.aerTab = "ejecutivo";
        env.styles.aer();
        env.render.aer();
      },
    },
    tabs: { aer: (env) => calls.push(["dispatch", env]) },
    shell: {
      mount: (root, env) => calls.push(["mount", root, env]),
      bind: (env) => ({
        select(tab) {
          env.tab(tab === "minutas" ? "ia" : tab);
          env.render();
          if (env.tab() === "ia")
            for (const name of [
              "analysis",
              "minutes",
              "config",
              "summary",
              "parts",
            ])
              env.loads[name]();
        },
        refresh: () => env.apply({ proyecto: { id: "P" } }, env.tab()),
      }),
    },
  };
  return {
    store,
    calls,
    services,
    runtime: createAerRuntime(store, services),
    setIxs: (value) => {
      ixs = value;
    },
  };
}
test("initial mount and panel contexts use the shared modular store", (t) => {
  const { runtime, store, calls, services } = setup(t);
  runtime.initialize(store.aer);
  assert.equal(calls.at(-1)[0], "mount");
  assert.equal(calls.at(-1)[2].project, store.aer);
  const plan = runtime.planningContext();
  assert.equal(plan.range(), store.aerPlanningRange);
  assert.equal(plan.saving, services.feedback.saving);
  assert.equal(runtime.effortContext().state(), store.aerRecords);
  runtime.resourcesContext().selected("Ana");
  assert.equal(store.aerResourceSelection, "Ana");
  runtime.dispatch();
  assert.equal(calls.at(-1)[1].aer(), store.aer);
});
test("minutas alias loads five sources in the same order and refresh retains tab", (t) => {
  const { runtime, store, calls } = setup(t);
  runtime.select("minutas");
  assert.equal(store.aerTab, "ia");
  assert.deepEqual(
    calls
      .filter((x) =>
        ["analysis", "minutes", "config", "summary", "parts"].includes(x[0]),
      )
      .map((x) => x[0]),
    ["analysis", "minutes", "config", "summary", "parts"],
  );
  const ai = store.aerAi;
  runtime.refresh();
  assert.equal(store.aerTab, "ia");
  assert.equal(store.aerAi, ai);
  assert.equal(calls.at(-1)[0], "mount");
});
test("IA buttons preserve flags and use actions/sources/presentation directly", (t) => {
  const { runtime, calls } = setup(t),
    env = runtime.aiPresentationContext();
  env.actions.analyze(true);
  assert.deepEqual(calls.at(-1), ["analyze", true]);
  env.actions.saveConfig(false);
  assert.deepEqual(calls.at(-1), ["saveConfig", false]);
  env.actions.loadConfig(true);
  assert.deepEqual(calls.at(-1), ["config", true]);
  env.actions.files();
  assert.deepEqual(calls.at(-1), ["files", undefined]);
  env.actions.action();
  assert.deepEqual(calls.at(-1), ["action"]);
  env.actions.risk();
  assert.deepEqual(calls.at(-1), ["risk"]);
  runtime.sources();
  assert.deepEqual(runtime.aiData(), { id: "P" });
});
test("shared IXS Actions and Communiqués preserve family and project fields", (t) => {
  const { runtime, store, calls, setIxs } = setup(t);
  setIxs(true);
  store.ixsTab = "acciones";
  assert.equal(runtime.actionsContext().family, "ixs");
  runtime.tabs().selectIxs("recursos");
  assert.deepEqual(calls.at(-1), ["ixs-tab", "recursos"]);
  setIxs(false);
  runtime.planningContext().communique();
  assert.deepEqual(calls.at(-1), [
    "communique",
    { projectId: "P", projectName: "Proyecto", family: "aer" },
  ]);
});
