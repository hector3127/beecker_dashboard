import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { createProjectPanels } from "../../frontend/static/scripts/pages/project_detail/sections/project_panels.js";
import { createProjectState } from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const bindings = {
  aerPlanFiltroMes: "aerPlanningRange",
  aerPlanTableFilters: "aerPlanningFilters",
  aerClockifyFiltro: "aerRecords",
  aerEvalRecursoSeleccionado: "aerResourceSelection",
  ixsPlanState: "ixsPlanning",
  ixsPlanAzureState: "ixsPlanningAzure",
  ixsAzureState: "ixsAzure",
};
for (const [name, key] of Object.entries(bindings)) {
  test(`${name}: panel defaults match previous and instances stay independent`, () => {
    const literal = source.match(
      new RegExp(
        `var ${name} = window\\.beeProjectState \\? window\\.beeProjectState\\.\\w+ : ([^\\n]+);`,
      ),
    )[1];
    const expected = JSON.parse(
      JSON.stringify(vm.runInNewContext(`(${literal})`)),
    );
    const a = createProjectState(),
      b = createProjectState();
    assert.deepEqual(a[key], expected);
    if (a[key] && typeof a[key] === "object") {
      assert.notEqual(a[key], b[key]);
      for (const field of Object.keys(a[key]))
        if (Array.isArray(a[key][field]))
          assert.notEqual(a[key][field], b[key][field]);
    }
  });
}
for (const [method, name, tab] of [
  ["effort", "aerEsfuerzoContexto", "esfuerzo"],
  ["planning", "aerPlaneacionContexto", "planeacion"],
  ["resources", "aerRecursosContexto", "recursos"],
]) {
  test(`${method}: context contract and lifecycle match previous`, () => {
    const store = createProjectState();
    store.aer = { proyecto: { id: "AER.001" } };
    store.aerTab = tab;
    const noop = () => {};
    const scope = {
      window: { beeProjectCommunique: {} },
      aerDashboardData: store.aer,
      aerTabActual: tab,
      _aerRenderTab: noop,
      showError: noop,
      aerAbrirComunicados: noop,
      aerRecargarProyecto: noop,
      _aerStartSaving: noop,
    };
    for (const [global, key] of Object.entries(bindings))
      scope[global] = store[key];
    vm.runInNewContext(
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
      scope,
    );
    const previous = scope[name]();
    const callbacks = { paint: noop, error: noop };
    if (method !== "effort") callbacks.saving = noop;
    if (method === "planning")
      Object.assign(callbacks, { reload: noop, communique: noop });
    const current = createProjectPanels(store)[method](callbacks);
    assert.deepEqual(Object.keys(current).sort(), Object.keys(previous).sort());
    assert.equal(current.dashboard, previous.dashboard);
    assert.equal(current.id, previous.id);
    assert.equal(current.current(), previous.current());
    assert.equal(current.active(), previous.active());
    for (const key of Object.keys(callbacks))
      assert.equal(current[key], previous[key]);
    if (method === "planning") {
      const range = { desde: "2026-04", hasta: "2026-06" },
        filters = { tipo: "Hito" };
      current.setRange(range);
      previous.setRange(range);
      current.setFilters(filters);
      previous.setFilters(filters);
      assert.equal(current.range(), previous.range());
      assert.equal(current.filters(), previous.filters());
    } else if (method === "effort") {
      const records = { registros: [{ id: 1 }], desde: "2026-01-01" };
      current.setState(records);
      previous.setState(records);
      assert.equal(current.state(), previous.state());
    } else {
      current.selected("Ana");
      previous.selected("Ana");
      assert.equal(current.selected(), previous.selected());
    }
    store.aerTab = scope.aerTabActual = "ia";
    assert.equal(current.active(), previous.active());
    store.aer = scope.aerDashboardData = { proyecto: { id: "OTHER" } };
    assert.equal(current.current(), previous.current());
    assert.equal(current.current(), false);
  });
}
