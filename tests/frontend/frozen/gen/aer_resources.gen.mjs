import fs from "node:fs";
import vm from "node:vm";
// Explicit temporary original-only generator.
const captured = [];
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
  for (const selected of ["", "Beto", "Sin evaluación", "Inexistente"]) {
    scope.aerDashboardData = structuredClone(dashboard);
    scope.aerEvalRecursoSeleccionado = selected;
    captured.push({
      label,
      dashboard: plain(dashboard),
      selected,
      expected: plain(scope._aerVistaRecursos()),
    });
  }
const tag = (value) =>
  value === undefined ? { kind: "undefined" } : { kind: "value", value };
const categories = [
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
].map((input) => ({
  input: tag(input),
  category: scope._aerEvalCategoria(input),
  className: scope._aerEvalClase(input),
}));
const before = process.env.TZ,
  dates = [];
try {
  for (const timezone of ["UTC", "America/Mexico_City"]) {
    process.env.TZ = timezone;
    dates.push({
      timezone,
      cases: [
        null,
        "",
        "2026-10-02",
        "2026-10-02T18:00:00Z",
        "02/10/2026",
        "bad",
        "October 2, 2026",
      ].map((input) => ({ input, expected: scope._aerDateKey(input) })),
    });
  }
} finally {
  if (before === undefined) delete process.env.TZ;
  else process.env.TZ = before;
}
fs.writeFileSync(
  "tests/frontend/frozen/aer_resources.json",
  JSON.stringify({ cases: captured, categories, dates }, null, 2) + "\n",
);
console.log(
  "Captured",
  captured.length,
  "resources,",
  categories.length,
  "boundaries and 7 dates in two timezones.",
);
