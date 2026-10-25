import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs
  .readFileSync(
    "frontend/static/scripts/pages/project_detail/sections/project_tabs.js",
    "utf8",
  )
  .replace(/import[^;]+;/, " ")
  .replace("export function", "function");
function setup(tab, shared = false) {
  const target = { isConnected: true },
    aer = { proyecto: { id: "AER" } },
    ixs = { proyecto: { id: "IXS" } },
    calls = [],
    contexts = [];
  let currentAer = aer,
    currentIxs = ixs,
    aerTab = tab,
    ixsTab = tab;
  const scope = {
    document: {
      getElementById: () => target,
      querySelector: () => (shared ? {} : null),
    },
    placeholder: (...args) => calls.push({ name: "placeholder", args }),
  };
  vm.runInNewContext(source, scope);
  const record =
    (name) =>
    (...args) =>
      calls.push({ name, args });
  const views = new Proxy(
    {},
    {
      get: (_, name) =>
        name === "beeProjectExecutive" ? record(name) : { mount: record(name) },
    },
  );
  const env = {
    aer: () => currentAer,
    ixs: () => currentIxs,
    aerTab: (...a) => (a.length ? (aerTab = a[0]) : aerTab),
    ixsTab: () => ixsTab,
    selectAer: record("selectAer"),
    selectIxs: record("selectIxs"),
    aerContexts: Object.fromEntries(
      ["planning", "effort", "risks", "actions", "resources", "ai"].map((k) => [
        k,
        () => {
          contexts.push(k);
          return { context: k };
        },
      ]),
    ),
    ixsStates: () => ({
      planning: { key: "plan" },
      planningAzure: { key: "planAzure" },
      azure: { key: "azure" },
    }),
    resources: record("resource-states"),
    openAi: record("ia"),
    loadClientActions: record("shared-client"),
    syncPlanningAzure: record("sync-plan"),
    syncAzure: record("sync-azure"),
    planningActions: { key: "actions" },
    createRaid: record("raid-form"),
    previous: record("previous"),
  };
  return {
    api: scope.createProjectTabs(views, record("aer-fallback")),
    env,
    calls,
    contexts,
    aer,
    ixs,
    target,
    change: () => {
      currentAer = {};
      currentIxs = {};
      aerTab = "other";
      ixsTab = "other";
    },
  };
}
for (const [tab, name, context] of [
  ["ejecutivo", "beeProjectExecutive"],
  ["planeacion", "beeAerPlanning", "planning"],
  ["esfuerzo", "beeAerEffort", "effort"],
  ["riesgos", "beeAerRisks", "risks"],
  ["acciones", "beeProjectActions", "actions"],
  ["recursos", "beeAerResources", "resources"],
  ["ia", "beeAerAiPresentation", "ai"],
  ["cliente", "beeProjectClient"],
  ["unknown", "aer-fallback"],
])
  test(`AER dispatch preserves lazy context and target: ${tab}`, () => {
    const x = setup(tab);
    x.api.aer(x.env);
    assert.equal(x.calls[0].name, name);
    assert.equal(x.calls[0].args[0], x.target);
    assert.deepEqual(x.contexts, context ? [context] : []);
    if (!context) assert.equal(x.calls[0].args[1], x.aer);
    if (tab === "cliente") {
      const life = x.calls[0].args[2];
      assert.equal(life.family, "aer");
      assert.equal(life.current(), true);
      assert.equal(life.active(), true);
      x.change();
      assert.equal(life.current(), false);
      assert.equal(life.active(), false);
    }
  });
for (const [tab, name] of [
  ["resumen", "beeIxsExecutive"],
  ["planeacion", "beeIxsPlanning"],
  ["esfuerzo", "beeIxsEffort"],
  ["recursos", "beeIxsResources"],
  ["azure", "beeIxsAzureTab"],
  ["riesgos", "beeIxsRaid"],
  ["cliente", "shared-client"],
  ["acciones", "shared-client"],
  ["ia", "ia"],
  ["comunicacion", "beeIxsCommunication"],
  ["unknown", "placeholder"],
])
  test(`IXS dispatch keeps mounts, states and lifecycle: ${tab}`, () => {
    const x = setup(tab);
    x.api.ixs(x.env);
    const call = x.calls.at(-1);
    assert.equal(call.name, name);
    if (["resumen", "esfuerzo"].includes(tab))
      assert.equal(x.calls[0].name, "resource-states");
    if (name.startsWith("bee")) {
      assert.equal(call.args[0], x.target);
      assert.equal(call.args[1], x.ixs);
      const life = call.args.at(-1);
      const lifecycle = tab === "riesgos" ? call.args[2] : life;
      assert.equal(lifecycle.current(x.ixs), true);
      assert.equal(lifecycle.active(), true);
      if (tab === "planeacion") {
        assert.equal(call.args[2].key, "plan");
        assert.equal(call.args[3].key, "planAzure");
        assert.equal(lifecycle.actions, x.env.planningActions);
        assert.equal(lifecycle.resources, x.env.resources);
      }
      if (tab === "azure") assert.equal(call.args[2].key, "azure");
      x.change();
      assert.equal(lifecycle.current(x.ixs), false);
      assert.equal(lifecycle.active(), false);
    }
  });
test("IXS Client uses AER presenter with IXS scope and syncs tab", () => {
  const x = setup("cliente", true);
  x.env.aerTab("riesgos");
  x.api.aer(x.env);
  assert.equal(x.env.aerTab(), "cliente");
  assert.equal(x.calls[0].name, "beeProjectClient");
  assert.equal(x.calls[0].args[2].family, "ixs");
});
