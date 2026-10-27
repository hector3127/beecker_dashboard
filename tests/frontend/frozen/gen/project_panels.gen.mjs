// Temporary original-only capture; run from repository root.
const captured = { defaults: [], contracts: [] };
const test = (_name, callback) => callback();
import fs from "node:fs";
import vm from "node:vm";
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
    captured.defaults.push({ name, key, expected });
  });
}
for (const [method, name, tab] of [
  ["effort", "aerEsfuerzoContexto", "esfuerzo"],
  ["planning", "aerPlaneacionContexto", "planeacion"],
  ["resources", "aerRecursosContexto", "recursos"],
]) {
  test(`${method}: context contract and lifecycle match previous`, () => {
    const store = Object.fromEntries(
      captured.defaults.map(({ key, expected }) => [
        key,
        structuredClone(expected),
      ]),
    );
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
    const entry = {
      method,
      name,
      tab,
      keys: Object.keys(previous).sort(),
      dashboard: JSON.parse(JSON.stringify(previous.dashboard)),
      id: previous.id,
      current: previous.current(),
      active: previous.active(),
      callbacks: Object.keys(callbacks).map((key) => ({
        key,
        same: previous[key] === callbacks[key],
      })),
    };
    if (method === "planning") {
      const range = { desde: "2026-04", hasta: "2026-06" },
        filters = { tipo: "Hito" };
      previous.setRange(range);
      previous.setFilters(filters);
      entry.update = {
        range: previous.range(),
        filters: previous.filters(),
        sameRange: previous.range() === range,
        sameFilters: previous.filters() === filters,
      };
    } else if (method === "effort") {
      const records = { registros: [{ id: 1 }], desde: "2026-01-01" };
      previous.setState(records);
      entry.update = {
        records: previous.state(),
        same: previous.state() === records,
      };
    } else {
      previous.selected("Ana");
      entry.update = { selected: previous.selected() };
    }
    scope.aerTabActual = "ia";
    entry.inactive = previous.active();
    scope.aerDashboardData = { proyecto: { id: "OTHER" } };
    entry.replaced = previous.current();
    captured.contracts.push(entry);
  });
}

fs.writeFileSync(
  "tests/frontend/frozen/project_panels.json",
  JSON.stringify(captured, null, 2) + "\n",
);
