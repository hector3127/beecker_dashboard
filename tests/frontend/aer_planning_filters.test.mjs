import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  emptyFilters,
  initialRange,
  rowMatches,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_planning_filters_model.js";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const scope = {
  window: {},
  Date: class extends Date {
    constructor(...args) {
      super(...(args.length ? args : ["2026-10-24T18:00:00Z"]));
    }
  },
};
for (const name of [
  "_aerNormFilter",
  "aerAplicarFiltrosPlan",
  "_aerInitPlanFiltroMes",
])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
vm.runInNewContext(source.match(/  function _aerMonthValue[^\n]+/)[0], scope);
const rows = [
  {
    tipo: "Actividad",
    actividad: "Revisión técnica",
    responsable: "Ana",
    estado: "Completado",
    compromiso: "2026-10-24",
    cierre: "2026-10-23",
  },
  {
    tipo: "Hito",
    actividad: "Entrega",
    responsable: "Sin responsable",
    estado: "Por validar",
    compromiso: "2026-10-25",
    cierre: "",
  },
  {
    tipo: "Actividad",
    actividad: "Diseño",
    responsable: "Beto",
    estado: "En progreso",
    compromiso: "",
    cierre: "",
  },
];
for (const patch of [
  {},
  { tipo: "Hito" },
  { actividad: "revision TECNICA" },
  { actividad: "ñ" },
  { responsable: "Ana" },
  { responsable: "ana" },
  { estado: "Por validar" },
  { compromisoDesde: "2026-10-24", compromisoHasta: "2026-10-24" },
  { cierreDesde: "2026-10-23", cierreHasta: "2026-10-23" },
  { compromisoDesde: "2026-10-25", compromisoHasta: "2026-10-24" },
  { actividad: "entrega", estado: "Completado" },
  { cierreDesde: "2026-10-24" },
]) {
  test(`Filters retain original row matching ${JSON.stringify(patch)}`, () => {
    const filters = { ...emptyFilters(), ...patch };
    const elements = rows.map((dataset) => ({ dataset, style: {} }));
    scope.aerPlanTableFilters = filters;
    scope.document = {
      querySelectorAll: () => elements,
      getElementById: () => null,
    };
    scope.aerAplicarFiltrosPlan();
    assert.deepEqual(
      rows.map((row) => rowMatches(row, filters)),
      elements.map((row) => row.style.display !== "none"),
    );
  });
}
test("Range initialization matches original and retains both chosen months", () => {
  for (const range of [
    {},
    { desde: "2026-01", hasta: "" },
    { desde: "", hasta: "2026-12" },
    { desde: "2026-12", hasta: "2026-01" },
  ]) {
    scope.aerPlanFiltroMes = { ...range };
    scope._aerInitPlanFiltroMes();
    assert.deepEqual(
      initialRange(range, new Date("2026-10-24T18:00:00Z")),
      JSON.parse(JSON.stringify(scope.aerPlanFiltroMes)),
    );
  }
});
