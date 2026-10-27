import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
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
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/project_state.json", import.meta.url),
    "utf8",
  ),
);

test("recorded legacy cells bind to the store without resetting existing values", () => {
  assert.equal(frozen.defaults.length, 23);
  const clean = createProjectState();
  for (const { key, expected } of frozen.defaults)
    assert.deepEqual(clean[key], expected, key);
  const state = createProjectState();
  state.aer = { cached: true };
  state.request = 7;
  const report = { filas: [{ id: "P" }] };
  state.reportAer = report;
  state.reportConsumptionRequest = 4;
  state.reportsStarted = true;
  const scope = {};
  bindProjectState(scope, state);
  assert.deepEqual(
    Object.keys(scope).sort(),
    frozen.defaults.map((x) => x.name).sort(),
  );
  for (const { name, key } of frozen.defaults)
    assert.equal(scope[name], state[key], name);
  scope.aerTabActual = "planeacion";
  scope.dashboardRequestSeq++;
  assert.equal(state.aer.cached, true);
  assert.equal(state.aerTab, "planeacion");
  assert.equal(state.request, 8);
  assert.equal(scope.cacheReporteAERTYM, report);
  assert.equal(state.reportConsumptionRequest, 4);
  assert.equal(state.reportsStarted, true);
  scope.cacheReporteIXB = scope.cacheReporteAERTYM;
  scope.reporteAERConsumosSecuencia++;
  assert.equal(state.reportIxs, report);
  assert.equal(state.reportConsumptionRequest, 5);
  assert.equal(createProjectState().reportAer, null);
  assert.equal(createProjectState().reportsStarted, false);
  assert.equal(scope.ixsClienteAccionesCache, state.clientCache);
  state.ixs = { proyecto: { id: "P" } };
  assert.equal(scope.ixsProyectoActual, state.ixs);
});
