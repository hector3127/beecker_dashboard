import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  context,
  facts,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_ai_model.js";
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
vm.runInNewContext(source.match(/  function aerIAHoy[^\n]+/)[0], scope);
for (const name of ["aerIAContexto", "aerIAHechos"])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
const plain = (x) => JSON.parse(JSON.stringify(x));
const fixture = JSON.parse(
  fs.readFileSync("tests/aer/aer_expected.json", "utf8"),
).results[3];
const full = {
  ...fixture,
  kpis: { ...fixture.kpis, horasTotales: 110, budgetHoras: 100 },
  plan: {
    filas: Array.from({ length: 32 }, (_, i) => ({
      actividad: `Tarea ${i}`,
      responsable: i % 2 ? "Ana" : "Pendiente",
      esfuerzo: 2,
      estado: i % 3 ? "En progreso" : "Completado",
      finPlan: i % 2 ? "2026-10-22" : "2026-11-10",
    })),
  },
  vacaciones: {
    filas: [
      {
        recurso: "Ana",
        inicio: "2026-10-24",
        fin: "2026-10-25",
        estado: "Aprobada",
      },
      {
        recurso: "Beto",
        inicio: "2026-10-24",
        fin: "2026-10-25",
        estado: "Pendiente",
      },
    ],
  },
};
for (const [label, dashboard] of [
  ["empty", {}],
  ["fixture", fixture],
  ["overload and truncation", full],
])
  for (const state of [
    {},
    {
      accionesPartes: [
        { accion: "A", estado: "Completado" },
        { accion: "B", estado: "completado" },
        { accion: "C", estado: "Pendiente" },
      ],
    },
  ])
    test(`AER context and facts match original: ${label}/${!!state.accionesPartes}`, () => {
      scope.aerDashboardData = dashboard;
      scope.aerIAState = state;
      const before = JSON.stringify([dashboard, state]);
      const now = new Date("2026-10-23T18:00:00Z");
      assert.deepEqual(
        plain(context(dashboard, state, now)),
        plain(scope.aerIAContexto()),
      );
      assert.deepEqual(
        plain(facts(dashboard, state, now)),
        plain(scope.aerIAHechos()),
      );
      assert.equal(JSON.stringify([dashboard, state]), before);
    });
