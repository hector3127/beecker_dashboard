import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { createProjectCompatibility } from "../../frontend/static/scripts/pages/project_detail/sections/project_compatibility.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const bridge = source.match(
  /  function projectCompatibilityBindings\([\s\S]*?\n  \}/,
)[0];

function scenario(modern, before, after, cached, hasSelect = true) {
  const calls = [],
    project = { value: "P" };
  let account = before;
  let aer = cached ? { aer: 1 } : null,
    ixs = cached ? { ixs: 1 } : null;
  const provider = {
    start: (...args) => {
      calls.push(["start", ...args]);
      return "started";
    },
    load: (...args) => {
      calls.push(["load", ...args]);
      return "loaded";
    },
    account: () => account,
    refresh: () => {
      calls.push(["refresh"]);
      account = after;
    },
    aer: () => aer,
    ixs: () => ixs,
    renderAer: (value) => {
      calls.push(["aer", value]);
    },
    renderIxs: (value) => {
      calls.push(["ixs", value]);
    },
    risks: () => calls.push(["risks"]),
    executive: () => {},
  };
  const doc = { getElementById: () => (hasSelect ? project : null) };
  let bindings;
  if (modern) bindings = createProjectCompatibility(doc).bindings(provider);
  else {
    const context = {
      window: {},
      document: doc,
      _clienteSeleccionadoDashboard: provider.account,
      cacheReporteAERTYM: aer,
      cacheReporteIXB: ixs,
      initDashboard: () => provider.start(),
      loadDashboard: (previous) =>
        previous ? provider.load() : provider.refresh(),
      renderReporteAERTYM: provider.renderAer,
      renderReporteIXBRaaS: provider.renderIxs,
      cargarTopRiesgosAzurePortafolio: provider.risks,
      renderDashboardEjecutivoProyecto: provider.executive,
    };
    vm.runInNewContext(bridge, context);
    bindings = context.projectCompatibilityBindings();
  }
  return {
    provider,
    bindings,
    calls,
    project,
    updateCache(value) {
      aer = value;
      ixs = value;
    },
  };
}

test("client contract preserves original order and account recheck after refresh", () => {
  for (const before of ["", "ACME"])
    for (const after of ["", "OTHER"])
      for (const cached of [false, true])
        for (const selected of [false, true]) {
          const old = scenario(false, before, after, cached, selected),
            modern = scenario(true, before, after, cached, selected);
          old.bindings.clientChanged();
          modern.bindings.clientChanged();
          assert.deepEqual(modern.calls, old.calls);
          assert.equal(modern.project.value, old.project.value);
        }
});

test("callbacks retain identity, arguments, result and synchronous invocation", () => {
  const s = scenario(true, "", "", false);
  assert.equal(s.bindings.previousStart, s.provider.start);
  assert.equal(s.bindings.previousLoad, s.provider.load);
  assert.equal(s.bindings.executive, s.provider.executive);
  assert.equal(s.bindings.previousStart("a"), "started");
  assert.equal(s.bindings.previousLoad("b"), "loaded");
  assert.deepEqual(s.calls, [
    ["start", "a"],
    ["load", "b"],
  ]);
});

test("report caches are read at the time of change, not when bindings are built", () => {
  const s = scenario(true, "", "", false),
    latest = { cut: "new" };
  s.updateCache(latest);
  s.bindings.clientChanged();
  assert.deepEqual(s.calls, [
    ["refresh"],
    ["aer", latest],
    ["ixs", latest],
    ["risks"],
  ]);
});

test("store-owned reports retain original account selection and refresh ordering", () => {
  for (const before of ["", " Todos los clientes ", "ACME"])
    for (const after of ["", "TODOS LOS CLIENTES", "OTHER"])
      for (const cached of [false, true]) {
        const calls = [],
          project = { value: "P" },
          client = { value: before };
        const state = { reportAer: null, reportIxs: null };
        const latest = cached ? { filas: [{ id: "current" }] } : null;
        const api = createProjectCompatibility({
          getElementById: (id) => (id === "f-cliente" ? client : project),
        });
        const bindings = api.reports(state, {
          refresh() {
            calls.push("refresh");
            client.value = after;
            state.reportAer = latest;
            state.reportIxs = latest;
          },
          renderAer: (value) => calls.push(["aer", value]),
          renderIxs: (value) => calls.push(["ixs", value]),
          risks: () => calls.push("risks"),
        });
        bindings.clientChanged();
        const account = (value) =>
          value.trim() && !/^todos los clientes$/i.test(value.trim());
        assert.equal(
          project.value,
          account(before) ? "Todos los proyectos" : "P",
        );
        assert.deepEqual(
          calls,
          account(after)
            ? ["refresh"]
            : [
                "refresh",
                ...(cached
                  ? [
                      ["aer", latest],
                      ["ixs", latest],
                    ]
                  : []),
                "risks",
              ],
        );
      }
});

test("store reports handle absent client and project selectors", () => {
  const calls = [];
  createProjectCompatibility({ getElementById: () => null })
    .reports(
      { reportAer: null, reportIxs: null },
      {
        refresh: () => calls.push("refresh"),
        risks: () => calls.push("risks"),
      },
    )
    .clientChanged();
  assert.deepEqual(calls, ["refresh", "risks"]);
});
