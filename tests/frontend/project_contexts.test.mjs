import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { createProjectContexts } from "../../frontend/static/scripts/pages/project_detail/sections/project_contexts.js";
import {
  createProjectState,
  bindProjectState,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
function setup() {
  const store = createProjectState(),
    calls = [];
  store.aer = { proyecto: { id: "AER" } };
  store.ixs = { proyecto: { id: "IXS" } };
  const scope = { window: {}, ixsClienteAccionesCache: store.clientCache };
  bindProjectState(scope, store);
  for (const name of [
    "initDashboard",
    "loadDashboard",
    "renderDashboardAERTYMProyecto",
    "renderDashboardIXBSaaSRaaS",
    "renderDashboardEjecutivoProyecto",
    "_aerEnsureStyles",
    "_ixsEnsureStyles",
    "ixsIAStyles",
    "_aerRenderShell",
    "_ixsRenderShell",
    "_aerRenderTab",
    "_ixsRenderTab",
    "ixsIAPintar",
    "ixsIACargarFuentes",
    "ixsIACargarHistoria",
    "ixsIACargarDrive",
    "showError",
    "aerIACargarAnalisis",
    "aerIACargarMinutas",
    "aerIACargarConfigMinutas",
    "aerIACargarResumenEjecutivo",
    "aerIACargarAccionesPartes",
    "aerCambiarTab",
    "ixsCambiarTab",
    "aerPlaneacionContexto",
    "aerEsfuerzoContexto",
    "aerRiesgosContexto",
    "aerAccionesContexto",
    "aerRecursosContexto",
    "aerIAPresentacionContexto",
    "_ixsCargarEstadosRecursos",
    "ixsIAAbrir",
    "ixsCargarClienteAcciones",
    "ixsRaidAbrirCrear",
    "ixsAbrirVistaAnterior",
    "ixsAbrirPlanEditor",
    "ixsEditarHitoTimeline",
    "ixsAbrirExtension",
  ])
    scope[name] = (...args) => calls.push([name, ...args]);
  for (const name of [
    "projectEntryContext",
    "projectSessionContext",
    "projectShellContext",
    "projectTabsContext",
  ])
    vm.runInNewContext(
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
      scope,
    );
  return { store, scope, calls, contexts: createProjectContexts(store) };
}
const sameKeys = (a, b) =>
  assert.deepEqual(Object.keys(a).sort(), Object.keys(b).sort());

test("entry contract keeps metadata references, callbacks and invalidation", () => {
  const { store, scope, contexts } = setup(),
    old = scope.projectEntryContext();
  const next = contexts.entry({
    previousStart: old.previousStart,
    previousLoad: old.previousLoad,
    clientChanged: old.clientChanged,
    render: old.render,
  });
  sameKeys(next, old);
  assert.equal(next.render, old.render);
  assert.equal(next.clientChanged, old.clientChanged);
  const metadata = { P: { servicio: "IXB" } };
  old.metadata(metadata);
  assert.equal(next.metadata(), metadata);
  next.metadata({});
  assert.equal(old.metadata(), store.metadata);
  old.invalidatePrevious();
  next.invalidatePrevious();
  assert.equal(store.request, 2);
});
test("session contract exposes the same mutable cells and cache", () => {
  const { store, scope, contexts } = setup(),
    old = scope.projectSessionContext();
  const next = contexts.session({
    styles: old.styles,
    render: old.render,
    aiLoads: old.aiLoads,
  });
  sameKeys(next, old);
  for (const key of [
    "aer",
    "ixs",
    "aerAi",
    "ixsAi",
    "clockify",
    "aerTab",
    "ixsTab",
  ]) {
    const value = { key };
    old[key](value);
    assert.equal(next[key](), value);
    next[key](null);
    assert.equal(old[key](), null);
  }
  next.globalId("P");
  assert.equal(scope.idProyectoActualGlobal, "P");
  old.globalId("Q");
  assert.equal(store.projectId, "Q");
  assert.equal(next.cache, old.cache);
});
for (const family of ["aer", "ixs"])
  test(`${family}: shell snapshot, refresh and lifecycle match previous`, (t) => {
    const { store, scope, contexts, calls } = setup();
    let present = true;
    const document = { querySelector: () => (present ? {} : null) },
      previousDocument = globalThis.document;
    globalThis.document = scope.document = document;
    t.after(() => {
      globalThis.document = previousDocument;
    });
    const old = scope.projectShellContext(family);
    const next = contexts.shell(family, {
      render: old.render,
      dispatch: old.dispatch,
      error: old.error,
      loads: old.loads,
      initializeIxs: scope.renderDashboardIXBSaaSRaaS,
    });
    sameKeys(next, old);
    assert.equal(next.project, old.project);
    assert.equal(next.current(), old.current());
    present = false;
    assert.equal(next.current(), old.current());
    present = true;
    old.tab("planeacion");
    assert.equal(next.tab(), "planeacion");
    next.tab("ia");
    assert.equal(old.tab(), "ia");
    store.clientCache.IXS = { cached: true };
    const result = { proyecto: { id: "updated" } };
    old.apply(result, "recursos");
    const first = calls.pop();
    store.clientCache.IXS = { cached: true };
    next.apply(result, "recursos");
    assert.deepEqual(calls.pop(), first);
    if (family === "aer") {
      assert.equal(store.aer, result);
      assert.equal(store.aerTab, "recursos");
    } else assert.equal(store.clientCache.IXS, undefined);
    store[family] = null;
    assert.equal(next.current(), old.current());
  });
test("tabs preserve lazy panel states, Azure synchronization and encoded editor IDs", () => {
  const { store, scope, contexts, calls } = setup(),
    old = scope.projectTabsContext();
  const next = contexts.tabs({
    selectAer: old.selectAer,
    selectIxs: old.selectIxs,
    aerContexts: old.aerContexts,
    resources: old.resources,
    openAi: old.openAi,
    loadClientActions: old.loadClientActions,
    createRaid: old.createRaid,
    previous: old.previous,
    editPlanning: scope.ixsAbrirPlanEditor,
    editMarker: old.planningActions.editMarker,
    extension: old.planningActions.extension,
  });
  sameKeys(next, old);
  sameKeys(next.planningActions, old.planningActions);
  assert.equal(next.aerContexts, old.aerContexts);
  const azure = { items: [] };
  old.syncAzure(azure);
  assert.equal(next.ixsStates().azure, azure);
  next.syncPlanningAzure("P", [1]);
  assert.equal(old.ixsStates().azure.items[0], 1);
  store.ixsPlanning = { fresh: true };
  assert.equal(next.ixsStates().planning, old.ixsStates().planning);
  const initial = { fecha: "2026-10-23" };
  old.planningActions.edit("Hito", "Á' /&", initial);
  const first = calls.pop();
  next.planningActions.edit("Hito", "Á' /&", initial);
  assert.deepEqual(calls.pop(), first);
  old.planningActions.azure();
  const selected = calls.pop();
  next.planningActions.azure();
  assert.deepEqual(calls.pop(), selected);
});
