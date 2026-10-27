import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  resourcesModel,
  category,
  categoryClass,
  dateKey,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_resources_model.js";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const scope = { window: {} };
for (const name of ["_aerDateKey", "_aerRecursosProyecto"])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
for (const name of ["_aerEvalCategoria", "_aerEvalClase"])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}[^\\n]+`))[0],
    scope,
  );
const start = source.indexOf("  function _aerVistaRecursos()");
vm.runInNewContext(
  source.slice(
    start,
    source.indexOf('    return `<div class="aer-vivid-grid">', start),
  ) +
    "return {ev,evOrdenadas,recursos,selected:aerEvalRecursoSeleccionado,porRecurso,latest,avg,pendientes,observacion,top,hist,sel,pts,xs,ys,poly,ptsDelta,cats,totalCat,a1,a2,a3,prox,strengths};\n}",
  scope,
);
const plain = (value) => JSON.parse(JSON.stringify(value));
const rows = Array.from({ length: 8 }, (_, i) => ({
  recurso: i % 2 ? "Ana" : "Beto",
  score: 50 + i * 7,
  fechaEvaluacion: `2026-10-${i + 1}`,
  proximaEvaluacion: "2026-09-01",
  calidad: 90,
  cumplimiento: 80,
  comunicacion: 70,
  colaboracion: 60,
  autonomia: 50,
}));
for (const [label, dashboard] of [
  ["empty", {}],
  [
    "history",
    {
      evaluaciones: { filas: rows },
      detalleRecursos: [{ recurso: "Sin evaluación" }],
    },
  ],
  ["single", { evaluaciones: { filas: rows.slice(0, 1) } }],
  [
    "mixed dates",
    {
      evaluaciones: {
        filas: [
          ...rows,
          { recurso: "Ana", score: 90, fechaEvaluacion: "12/10/2026" },
          { recurso: "Ana", score: 91, fechaEvaluacion: "12/10/2026" },
        ],
      },
      plan: {
        filas: [{ responsable: "Pendiente" }, { responsable: " Otro " }],
      },
    },
  ],
])
  for (const selected of ["", "Beto", "Sin evaluación", "Inexistente"])
    test(`Resource summary matches original: ${label}/${selected}`, () => {
      const before = JSON.stringify(dashboard);
      scope.aerDashboardData = dashboard;
      scope.aerEvalRecursoSeleccionado = selected;
      assert.deepEqual(
        plain(resourcesModel(dashboard, selected)),
        plain(scope._aerVistaRecursos()),
      );
      assert.equal(JSON.stringify(dashboard), before);
    });
test("Category boundaries and date sorting preserve original behavior", () => {
  for (const value of [
    undefined,
    null,
    "",
    0,
    69,
    70,
    79,
    80,
    89,
    90,
    100,
    110,
    "85",
    "invalid",
  ]) {
    assert.equal(category(value), scope._aerEvalCategoria(value));
    assert.equal(categoryClass(value), scope._aerEvalClase(value));
  }
  for (const value of [
    null,
    "",
    "2026-10-02",
    "2026-10-02T18:00:00Z",
    "02/10/2026",
    "bad",
    "October 2, 2026",
  ])
    assert.equal(dateKey(value), scope._aerDateKey(value));
});
