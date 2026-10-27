// Temporary original-only capture; run from repository root.
import fs from "node:fs";
import vm from "node:vm";
const captured = [];
const test = (_name, callback) => callback();
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const bridge = source.match(
  /  function projectCompatibilityBindings\([\s\S]*?\n  \}/,
)[0];
test("compatibility bridge preserves account gate, cache rendering order and exact callbacks", () => {
  for (const account of ["", "ACME"])
    for (const cached of [false, true]) {
      const calls = [],
        select = { value: "P" };
      const context = {
        window: {},
        document: { getElementById: () => select },
        _clienteSeleccionadoDashboard: () => account,
        initDashboard: (...args) => calls.push(["start", ...args]),
        loadDashboard: (...args) => calls.push(["load", ...args]),
        cacheReporteAERTYM: cached ? { aer: 1 } : null,
        cacheReporteIXB: cached ? { ixs: 1 } : null,
        renderReporteAERTYM: (data) => calls.push(["aer", data]),
        renderReporteIXBRaaS: (data) => calls.push(["ixs", data]),
        cargarTopRiesgosAzurePortafolio: () => calls.push(["risks"]),
        renderDashboardEjecutivoProyecto: () => {},
      };
      vm.runInNewContext(bridge, context);
      const bindings = context.projectCompatibilityBindings();
      bindings.previousStart();
      bindings.previousLoad();
      bindings.clientChanged();
      captured.push({
        account,
        cached,
        calls,
        selected: select.value,
        keys: Object.keys(bindings).sort(),
        sameExecutive:
          bindings.executive === context.renderDashboardEjecutivoProyecto,
      });
    }
});
fs.writeFileSync(
  "tests/frontend/frozen/project_script_loader.json",
  JSON.stringify(captured, null, 2) + "\n",
);
