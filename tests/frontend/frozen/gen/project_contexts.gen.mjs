// Temporary original-only capture.
import fs from "node:fs";
import {
  originalState,
  load,
  plain,
  describe,
  stub,
} from "./project_original_state.mjs";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const callbackNames = [
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
];
function setup() {
  const { store, scope } = originalState(source);
  const calls = [];
  store.aer = { proyecto: { id: "AER" } };
  store.ixs = { proyecto: { id: "IXS" } };
  stub(scope, calls, callbackNames);
  load(source, scope, [
    "projectEntryContext",
    "projectSessionContext",
    "projectShellContext",
    "projectTabsContext",
  ]);
  return { store, scope, calls };
}
const captured = {};
{
  const { store, scope } = setup(),
    old = scope.projectEntryContext();
  const metadata = { P: { servicio: "IXB" } };
  old.metadata(metadata);
  const sameMetadata = old.metadata() === metadata;
  old.metadata({});
  old.invalidatePrevious();
  old.invalidatePrevious();
  captured.entry = {
    keys: Object.keys(old).sort(),
    callbacks: describe({
      previousStart: old.previousStart,
      previousLoad: old.previousLoad,
      clientChanged: old.clientChanged,
      render: old.render,
    }),
    sameMetadata,
    metadata: plain(old.metadata()),
    request: store.request,
  };
}
{
  const { store, scope } = setup(),
    old = scope.projectSessionContext();
  const cells = [];
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
    const same = old[key]() === value;
    old[key](null);
    cells.push({ key, same, cleared: old[key]() });
  }
  old.globalId("P");
  const first = store.projectId;
  old.globalId("Q");
  captured.session = {
    keys: Object.keys(old).sort(),
    callbacks: describe({
      styles: old.styles,
      render: old.render,
      aiLoads: old.aiLoads,
    }),
    cells,
    first,
    second: store.projectId,
    cacheSame: old.cache === store.clientCache,
  };
}
captured.shells = [];
for (const family of ["aer", "ixs"]) {
  const { store, scope, calls } = setup();
  let present = true;
  scope.document = { querySelector: () => (present ? {} : null) };
  const old = scope.projectShellContext(family),
    project = plain(old.project);
  // Observe wrapper delegation rather than guessing its callback name.
  for (const key of ["render", "dispatch"]) {
    const start = calls.length;
    old[key]();
    const observed = calls.splice(start);
    if (observed.length !== 1) throw Error("Unexpected shell callback trace");
    old[key].__name = observed[0][0];
  }

  const current = old.current();
  present = false;
  const absent = old.current();
  present = true;
  old.tab("planeacion");
  const firstTab = old.tab();
  old.tab("ia");
  const secondTab = old.tab();
  store.clientCache.IXS = { cached: true };
  const result = { proyecto: { id: "updated" } };
  old.apply(result, "recursos");
  const applied = plain({
    calls,
    state: store[family],
    tab: store[family === "aer" ? "aerTab" : "ixsTab"],
    cache: store.clientCache,
  });
  store[family] = null;
  captured.shells.push({
    family,
    keys: Object.keys(old).sort(),
    project,
    callbacks: describe({
      render: old.render,
      dispatch: old.dispatch,
      error: old.error,
      loads: old.loads,
      initializeIxs: scope.renderDashboardIXBSaaSRaaS,
    }),
    current,
    absent,
    firstTab,
    secondTab,
    applied,
    replaced: old.current(),
  });
}
{
  const { store, scope, calls } = setup(),
    old = scope.projectTabsContext();
  const callbacks = describe({
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
  const azure = { items: [] };
  old.syncAzure(azure);
  const sameAzure = old.ixsStates().azure === azure;
  old.syncPlanningAzure("P", [1]);
  const synced = plain(old.ixsStates().azure);
  store.ixsPlanning = { fresh: true };
  const samePlanning = old.ixsStates().planning === store.ixsPlanning;
  const initial = { fecha: "2026-10-23" };
  old.planningActions.edit("Hito", "Á' /&", initial);
  old.planningActions.azure();
  captured.tabs = {
    keys: Object.keys(old).sort(),
    actionKeys: Object.keys(old.planningActions).sort(),
    callbacks,
    sameAzure,
    synced,
    samePlanning,
    calls: plain(calls),
  };
}
fs.writeFileSync(
  "tests/frontend/frozen/project_contexts.json",
  JSON.stringify(captured, null, 2) + "\n",
);
