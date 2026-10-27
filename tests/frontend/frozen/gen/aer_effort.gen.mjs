import fs from "node:fs";
import vm from "node:vm";
// Original-only capture, explicit temporary generator.
const captured = [];
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
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
    scope.aerDashboardData = structuredClone(dashboard);
    scope.aerClockifyFiltro = structuredClone(state);
    const expected = plain(scope._aerVistaEsfuerzo());
    captured.push({
      name,
      dashboard: plain(dashboard),
      state: plain(state),
      expected,
      expectedState: plain(scope.aerClockifyFiltro),
    });
  }
}
fs.writeFileSync(
  "tests/frontend/frozen/aer_effort.json",
  JSON.stringify(captured, null, 2) + "\n",
);
console.log("Captured", captured.length, "original effort cases");
