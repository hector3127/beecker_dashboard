// Temporary original-only capture.
const test = (_name, callback) => callback();
const captured = [];
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
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
  {
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
          const old = scenario(false, before, after, cached, selected);
          old.bindings.clientChanged();
          captured.push({
            before,
            after,
            cached,
            selected,
            expected: { calls: old.calls, selected: old.project.value },
          });
        }
});

fs.writeFileSync(
  "tests/frontend/frozen/project_compatibility.json",
  JSON.stringify(captured, null, 2) + "\n",
);
