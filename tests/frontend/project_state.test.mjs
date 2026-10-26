import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  createProjectState,
  bindProjectState,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";

test("each page owns independent caches, AI results and selections", () => {
  const a = createProjectState(),
    b = createProjectState();
  a.aerAi.seleccion.push("document");
  a.ixsAi.driveSelected.push("file");
  a.clientCache.P = {};
  a.metadata.P = {};
  a.milestones.push({});
  assert.deepEqual(b.aerAi.seleccion, []);
  assert.deepEqual(b.ixsAi.driveSelected, []);
  assert.deepEqual(b.clientCache, {});
  assert.deepEqual(b.metadata, {});
  assert.deepEqual(b.milestones, []);
  assert.equal(b.aerTab, "ejecutivo");
  assert.equal(b.ixsTab, "resumen");
});
test("compatibility callbacks read and replace the same state in both directions", () => {
  const target = {},
    state = createProjectState();
  bindProjectState(target, state);
  state.aer = { proyecto: { id: "AER" } };
  assert.equal(target.aerDashboardData, state.aer);
  const ai = { id: "IXS" };
  target.ixsIAState = ai;
  assert.equal(state.ixsAi, ai);
  target.dashboardRequestSeq++;
  assert.equal(state.request, 1);
  target.hitosAdicionalesActuales.push({ tipo: "Demo" });
  assert.equal(state.milestones.length, 1);
  bindProjectState(target, state);
  assert.equal(target.ixsIAState, ai);
});
test("real legacy declarations attach to the store without resetting existing values", () => {
  const source = fs.readFileSync(
    "apps/portal/static/portal/js/proyecto_detalle.js",
    "utf8",
  );
  const state = createProjectState();
  state.aer = { cached: true };
  state.request = 7;
  const report = { filas: [{ id: "P" }] };
  state.reportAer = report;
  state.reportConsumptionRequest = 4;
  state.reportsStarted = true;
  const scope = { beeProjectState: state };
  scope.window = scope;
  bindProjectState(scope, state);
  const declarations = source.match(
    /^  (?:var|const) \w+ = window\.beeProjectState[^\n]+/gm,
  );
  assert.equal(declarations.length, 23);
  vm.runInNewContext(
    declarations.join("\n") +
      "\naerTabActual='planeacion'; dashboardRequestSeq++;",
    scope,
  );
  assert.equal(state.aer.cached, true);
  assert.equal(state.aerTab, "planeacion");
  assert.equal(state.request, 8);
  assert.equal(vm.runInNewContext("cacheReporteAERTYM", scope), report);
  assert.equal(state.reportConsumptionRequest, 4);
  assert.equal(state.reportsStarted, true);
  vm.runInNewContext(
    "cacheReporteIXB=cacheReporteAERTYM; reporteAERConsumosSecuencia++;",
    scope,
  );
  assert.equal(state.reportIxs, report);
  assert.equal(state.reportConsumptionRequest, 5);
  assert.equal(createProjectState().reportAer, null);
  assert.equal(createProjectState().reportsStarted, false);
  assert.equal(
    vm.runInNewContext("ixsClienteAccionesCache", scope),
    state.clientCache,
  );
  state.ixs = { proyecto: { id: "P" } };
  assert.equal(vm.runInNewContext("ixsProyectoActual", scope), state.ixs);
});
