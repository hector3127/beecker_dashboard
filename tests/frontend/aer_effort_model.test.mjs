import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  effortModel,
  weekRange,
  initialState,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_effort_model.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const scope = {
  window: {},
  Date: class extends Date {
    constructor(...args) {
      super(...(args.length ? args : ["2026-10-23T18:00:00Z"]));
    }
  },
};
for (const name of [
  "_aerSemanaActual",
  "_aerInitClockifyFiltro",
  "_aerRegistrosClockifyActuales",
])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
const start = source.indexOf("  function _aerVistaEsfuerzo()");
vm.runInNewContext(
  source.slice(
    start,
    source.indexOf('    return `<div class="aer-vivid-grid">', start),
  ) +
    "return {k,tasks,recursos,trend,regs,previewCount,regsPreview,maxTask,maxMes,fact,noFact,outPct,totalPct};\n}",
  scope,
);
const data = JSON.parse(fs.readFileSync("tests/aer/aer_expected.json", "utf8"))
  .results[3];
const plain = (x) => JSON.parse(JSON.stringify(x));
for (const [name, dashboard] of [
  ["empty", {}],
  ["original", data],
  [
    "truncated",
    {
      ...data,
      tareas: Array.from({ length: 12 }, (_, i) => ({
        nombre: String(i),
        horas: i,
      })),
      detalleRecursos: Array.from({ length: 15 }, (_, i) => ({
        recurso: String(i),
      })),
    },
  ],
]) {
  for (const state of [
    { desde: "", hasta: "", registros: null, total: 0, cargando: false },
    { desde: "2026-08-01", hasta: "2026-10-01", registros: null },
    { desde: "2026-10-23", hasta: "2026-10-23", registros: [] },
    {
      desde: "2026-10-23",
      hasta: "2026-10-23",
      registros: Array.from({ length: 8 }, (_, i) => ({
        fecha: "2026-10-23",
        descripcion: String(i),
      })),
      total: 50,
      cargando: true,
    },
  ]) {
    test(`Effort summary, preview and range match original (${name}, ${state.registros?.length ?? "base"}, ${state.desde})`, () => {
      scope.aerDashboardData = dashboard;
      scope.aerClockifyFiltro = { ...state };
      const before = JSON.stringify([dashboard, state]);
      const { state: actualState, ...actual } = effortModel(
        dashboard,
        state,
        new Date("2026-10-23T18:00:00Z"),
      );
      assert.deepEqual(plain(actual), plain(scope._aerVistaEsfuerzo()));
      assert.deepEqual(plain(actualState), plain(scope.aerClockifyFiltro));
      assert.equal(JSON.stringify([dashboard, state]), before);
    });
  }
}
test("Default range retains Monday through Sunday and chosen dates", () => {
  for (const now of [
    "2026-10-19T18:00:00Z",
    "2026-10-23T18:00:00Z",
    "2026-10-25T18:00:00Z",
  ])
    assert.deepEqual(weekRange(new Date(now)), {
      desde: "2026-10-19",
      hasta: "2026-10-25",
    });
  assert.deepEqual(initialState({ desde: "2026-01-01", hasta: "2026-12-31" }), {
    desde: "2026-01-01",
    hasta: "2026-12-31",
  });
});
