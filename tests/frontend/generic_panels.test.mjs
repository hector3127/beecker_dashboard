import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  resourcesModel,
  resourceStateClass,
  shortDate,
  milestonesModel,
} from "../../frontend/static/scripts/pages/project_detail/sections/generic_panels_model.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const original = (name) =>
  vm.runInNewContext(
    "(" +
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0] +
      ")",
  );

test("resource badges keep all original state mappings including unknown values", () => {
  const badge = original("badgeEstadoClass");
  for (const state of [
    "Retrasado",
    "Excedido",
    "En riesgo",
    "En tiempo",
    "Sin estimacion en Recursos",
    "",
    null,
    undefined,
  ])
    assert.equal(resourceStateClass(state), badge(state));
});

test("milestone dates keep the original date formatter for valid, missing and invalid values", () => {
  const format = original("fmtFechaCorta");
  for (const value of [
    null,
    undefined,
    "",
    0,
    "bad",
    "2026-10-23",
    "2026-10-23T23:30:00Z",
    "2027-01-01T00:00:00Z",
    "23/10/2026",
  ])
    assert.equal(shortDate(value), format(value));
});

test("resource presentation keeps rounding/defaults and does not change source values", () => {
  const data = {
    filasRecursosCompleto: [
      {
        nombre: "Ana",
        costoReal: -1.5,
        costingRate: "22.50",
        horasReales: 0,
        estado: "Excedido",
      },
    ],
    totalesRecursos: {
      horasEstimadas: 12,
      horasReales: 0,
      costoReal: 1499.6,
      pctCumplimientoFinanciero: "62.7",
    },
  };
  const before = structuredClone(data),
    model = resourcesModel(data);
  assert.deepEqual(model.rows[0].cells, [
    "undefined",
    "Ana",
    "undefined",
    "$22.50",
    "undefined",
    "0",
    "undefined",
    "undefined",
    "undefined%",
    "$-1",
  ]);
  assert.equal(model.rows[0].badge, "badge-error");
  assert.deepEqual(model.totals, [
    "12",
    "0",
    "0",
    "0",
    "0%",
    "$" + (1500).toLocaleString(),
    "62.7% financiero",
  ]);
  assert.deepEqual(resourcesModel({}).rows, []);
  assert.deepEqual(resourcesModel({}).totals, [
    "0",
    "0",
    "0",
    "0",
    "0%",
    "$0",
    "0% financiero",
  ]);
  assert.deepEqual(data, before);
});

test("milestone grouping retains original order, additional notes and status fallback", () => {
  const rows = [
    {
      nombre: "A",
      estado: "Completado",
      esAdicional: false,
      observacion: "hidden",
    },
    {
      nombre: "B",
      estado: "Suspendida",
      esAdicional: true,
      observacion: "Nota",
    },
    { nombre: "C", estado: "Unknown" },
    { nombre: "D", estado: "En curso" },
    {
      nombre: "E",
      estado: "Completado",
      esAdicional: true,
      observacion: "Fin",
    },
  ];
  const before = structuredClone(rows),
    model = milestonesModel(rows);
  assert.deepEqual(
    model.upcoming.map((row) => row.name),
    ["B", "C", "D"],
  );
  assert.deepEqual(
    model.completed.map((row) => row.name),
    ["A", "E"],
  );
  assert.deepEqual(
    model.upcoming.map((row) => row.status),
    ["suspended", "pending", "running"],
  );
  assert.equal(model.upcoming[0].note, '"Nota"');
  assert.equal(model.completed[0].note, "");
  assert.equal(model.upcoming[1].subtitle, "Inicio: ? · Fin: ?");
  assert.deepEqual(rows, before);
});
