import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { createProjectScriptLoader } from "../../frontend/static/scripts/pages/project_detail/sections/project_script_loader.js";

function setup() {
  const scripts = [];
  const document = {
    createElement: () => ({
      dataset: {},
      remove() {
        this.removed = true;
      },
    }),
    head: { append: (script) => scripts.push(script) },
  };
  return { scripts, load: createProjectScriptLoader(document) };
}

test("concurrent and later bootstrap attempts evaluate each successful script once", async () => {
  const { scripts, load } = setup();
  const first = load("renderer.js", true),
    second = load("renderer.js", true);
  assert.equal(first, second);
  assert.equal(scripts.length, 1);
  assert.equal(scripts[0].dataset.projectBootstrap, "manual");
  scripts[0].onload();
  await first;
  await load("renderer.js", true);
  assert.equal(scripts.length, 1);
  const shim = load("shim.js");
  assert.equal(scripts[1].dataset.projectBootstrap, undefined);
  scripts[1].onload();
  await shim;
});

test("failed download is removed and can retry without reloading other successful scripts", async () => {
  const { scripts, load } = setup();
  const shim = load("shim.js");
  scripts[0].onload();
  await shim;
  const first = load("renderer.js", true);
  const failure = assert.rejects(
    first,
    /No se pudo cargar la interfaz del proyecto/,
  );
  scripts[1].onerror();
  await failure;
  assert.equal(scripts[1].removed, true);
  await load("shim.js");
  const retry = load("renderer.js", true);
  assert.equal(scripts.length, 3);
  scripts[2].onload();
  await retry;
});

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
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
      assert.deepEqual(calls.slice(0, 3), [
        ["start", true],
        ["load", true],
        ["load"],
      ]);
      assert.equal(select.value, account ? "Todos los proyectos" : "P");
      const after = calls.slice(3);
      assert.deepEqual(
        after,
        account
          ? []
          : cached
            ? [
                ["aer", context.cacheReporteAERTYM],
                ["ixs", context.cacheReporteIXB],
                ["risks"],
              ]
            : [["risks"]],
      );
      assert.equal(
        bindings.executive,
        context.renderDashboardEjecutivoProyecto,
      );
    }
});
