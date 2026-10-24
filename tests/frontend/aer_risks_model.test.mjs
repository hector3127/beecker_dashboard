import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  dedupRisks,
  risksModel,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_risks_model.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const now = "2026-10-23T18:00:00Z";
const scope = {
  window: {},
  Date: class extends Date {
    constructor(...args) {
      super(...(args.length ? args : [now]));
    }
  },
};
for (const name of [
  "_aerNormFilter",
  "_aerMergeByCompleteness",
  "_aerDedupRiesgosVista",
])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
const start = source.indexOf("  function _aerVistaRiesgos()");
vm.runInNewContext(
  source.slice(
    start,
    source.indexOf('    return `<div class="aer-vivid-grid">', start),
  ) +
    "return {r,k,ac,activos,crit,abiertos,matrix,hoyIso,vencidasAcc,exposure,abiertosCnt,mitigCnt,cerrCnt,atencion,riesgoPct,alerts:(aerDashboardData.alertas||[]).filter(x=>x.nivel!=='ok').length};\n}",
  scope,
);
const plain = (x) => JSON.parse(JSON.stringify(x));
const rows = [
  {
    uid: "a",
    riesgo: " Retraso ",
    responsable: "José",
    fechaLimite: "2026-10-01",
    estado: "Abierto",
    impacto: "Alto",
    probabilidad: "Media",
  },
  {
    uid: "b",
    riesgo: "retraso",
    responsable: "Jose",
    fechaLimite: "2026-10-01",
    accion: "Escalar",
    notas: "Seguimiento",
  },
  {
    uid: "c",
    riesgo: "Retraso",
    responsable: "Otra persona",
    fechaLimite: "2026-11-01",
    impacto: "Bajo",
  },
  { uid: "d", riesgo: "Otro", estado: "En progreso", probabilidad: "Alta" },
  { uid: "e", riesgo: "Resuelto", estado: "Resuelto", impacto: "Medio" },
  { uid: "f", riesgo: "Mitigado", estado: "Mitigado" },
  {
    uid: "g",
    riesgo: "Propuesto",
    estado: "Proposed",
    probabilidad: "Crítica",
  },
  { uid: "h", riesgo: "Sin estado", probabilidad: " Alta " },
  { uid: "i", riesgo: "Personalizado", estado: "Otro" },
  {},
];
for (const [name, dashboard] of [
  ["empty", {}],
  [
    "duplicates and statuses",
    {
      riesgos: { activos: rows },
      alertas: [{ nivel: "ok" }, { nivel: "warning" }],
    },
  ],
  [
    "attention fallback",
    {
      riesgos: { activos: rows.slice(3) },
      acciones: { vencidas: [{ fechaLimite: "2026-11-01" }] },
    },
  ],
  [
    "overdue attention",
    {
      riesgos: { activos: rows },
      acciones: {
        vencidas: [
          { fechaLimite: "2026-11-01" },
          { fechaLimite: "2026-10-22" },
          { fechaLimite: "2026-10-23" },
        ],
      },
      kpis: { healthScore: 80 },
    },
  ],
]) {
  test(`Risk summary matches original: ${name}`, () => {
    const before = JSON.stringify(dashboard);
    scope.aerDashboardData = dashboard;
    const old = scope._aerVistaRiesgos(),
      actual = risksModel(dashboard, new Date(now));
    assert.deepEqual(plain(actual), plain(old));
    for (const impacto of ["", "Bajo", "Medio", "Alto", "Crítico"])
      for (const probabilidad of ["", "Baja", "Media", "Alta", "Crítica"])
        assert.equal(
          actual.riesgoPct({ impacto, probabilidad }),
          old.riesgoPct({ impacto, probabilidad }),
        );
    assert.equal(JSON.stringify(dashboard), before);
  });
}
for (const variant of [
  [],
  rows,
  rows.slice().reverse(),
  [
    { riesgo: "Sin responsable" },
    { riesgo: "Sin responsable", responsable: "Ana", notas: "Más completo" },
  ],
])
  test(`Risk deduplication preserves original merging and ordering (${JSON.stringify(variant)})`, () => {
    const before = JSON.stringify(variant);
    assert.deepEqual(
      plain(dedupRisks(variant)),
      plain(scope._aerDedupRiesgosVista(variant)),
    );
    assert.equal(JSON.stringify(variant), before);
  });

test("Existing title grouping retains the first row even with distinct owners and dates", () => {
  assert.deepEqual(dedupRisks([rows[0], rows[2]]), [rows[0]]);
});
