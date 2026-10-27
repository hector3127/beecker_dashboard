// Temporary original-only capture.
import fs from "node:fs";
import vm from "node:vm";
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
function setup() {
  const { store, scope } = originalState(source, {
    window: {
      beeAerAiSources: { bind: (value) => value },
      beeAerAiActions: { bind: (value) => value },
    },
  });
  const calls = [];
  store.aer = { proyecto: { id: "P" } };
  store.ixs = { proyecto: { id: "P" } };
  store.aerAi.id = store.ixsAi.id = "P";
  stub(scope, calls, [
    "_aerRenderTab",
    "_aerToast",
    "_aerStartSaving",
    "showError",
    "aerIAContexto",
    "aerIAAbrirConfigMinutas",
    "aerIAPresentacionModular",
    "aerCambiarTab",
  ]);
  scope.aerAccionesModulares = () => ({ open: () => calls.push(["open"]) });
  load(source, scope, [
    "ixsCAActivo",
    "aerRiesgosContexto",
    "aerAccionesContexto",
    "aerIAFuentesModulares",
    "aerIAPresentacionContexto",
    "aerIAAccionesModulares",
  ]);
  return { store, scope, calls };
}
const captured = { actions: [], contracts: [] };
for (const family of ["aer", "ixs"]) {
  const { store, scope, calls } = setup();
  scope.document = { querySelector: () => (family === "ixs" ? {} : null) };
  store.aerTab = store.ixsTab = "acciones";
  store.clientCache.P = {};
  const old = scope.aerAccionesContexto();
  const entry = {
    family,
    keys: Object.keys(old).sort(),
    observedFamily: old.family,
    callbacks: describe({
      paint: old.paint,
      toast: old.toast,
      error: old.error,
    }),
  };
  const rows = { filas: [1] };
  old.actions(rows);
  entry.paints = calls.length;
  entry.sameActions = old.dashboard.acciones === rows;
  old.loadingParts(true);
  entry.partsLoading = old.partsLoading();
  const parts = [{ uid: "part" }];
  old.setParts(parts);
  entry.sameParts = old.parts() === parts;
  entry.cacheSame = store.clientCache.P.partes === parts;
  store.aerTab = store.ixsTab = "ia";
  entry.inactive = old.active();
  const count = calls.length;
  old.paintParts();
  entry.partsPaints = calls.length - count;
  const replacement = { filas: [] };
  old.storeActions(replacement);
  entry.stored = old.dashboard.acciones === replacement;
  store.aer = { proyecto: { id: "P" } };
  entry.replaced = old.current();
  captured.actions.push(entry);
}
for (const [method, name, keys, tab] of [
  [
    "risks",
    "aerRiesgosContexto",
    ["paint", "saving", "error", "openAction"],
    "riesgos",
  ],
  [
    "aerSources",
    "aerIAFuentesModulares",
    ["paint", "context", "toast", "openConfig"],
    "ia",
  ],
  [
    "aerPresentation",
    "aerIAPresentacionContexto",
    ["paint", "toast", "actions"],
    "ia",
  ],
  [
    "aerActions",
    "aerIAAccionesModulares",
    ["paint", "toast", "error", "context", "presentation", "sources", "tab"],
    "ia",
  ],
]) {
  const { store, scope } = setup();
  store.aerTab = tab;
  const old = scope[name]();
  const callbacks = describe(
    Object.fromEntries(keys.map((key) => [key, old[key]])),
  );
  const sameState = old.state === store.aerAi,
    sameDashboard = old.dashboard === store.aer;
  const guards = [old.current()],
    active = old.active();
  store.aerTab = "ejecutivo";
  const inactive = old.active();
  store.aer = { proyecto: { id: "P" } };
  guards.push(old.current());
  store.aerAi = { ...store.aerAi };
  guards.push(old.current());
  store.aer = { proyecto: { id: "OTHER" } };
  guards.push(old.current());
  captured.contracts.push({
    method,
    name,
    tab,
    keys: Object.keys(old).sort(),
    callbacks,
    sameState,
    sameDashboard,
    guards,
    active,
    inactive,
  });
}
{
  const { store, scope } = setup();
  const expression = source.match(
    /current:window\.beeProjectFeatureContexts\?window\.beeProjectFeatureContexts\.ixsCurrent:state=>([^\n]+),/,
  )[1];
  const original = vm.runInContext(`state=>${expression}`, scope),
    state = store.ixsAi;
  const result = [original(state), original({ ...state }), original(null)];
  store.ixs = { proyecto: { id: "OTHER" } };
  result.push(original(state));
  store.ixs = null;
  result.push(original(state));
  captured.ixsGuards = result;
}
fs.writeFileSync(
  "tests/frontend/frozen/project_feature_contexts.json",
  JSON.stringify(captured, null, 2) + "\n",
);
