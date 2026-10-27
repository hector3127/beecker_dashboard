import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  resourcesModel,
  resourceStateClass,
  shortDate,
  milestonesModel,
} from "../../frontend/static/scripts/pages/project_detail/sections/generic_panels_model.js";

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/generic_panel_helpers.json", import.meta.url),
    "utf8",
  ),
);
const restore = (input) =>
  input.kind === "undefined" ? undefined : input.value;
test("resource badges keep all original state mappings including unknown values", () => {
  assert.equal(frozen.badges.length, 8);
  for (const { input, expected } of frozen.badges)
    assert.equal(resourceStateClass(restore(input)), expected);
});
test("milestone dates keep the original date formatter for valid, missing and invalid values", () => {
  assert.deepEqual(
    frozen.dates.map((x) => x.timezone),
    ["UTC", "America/Mexico_City"],
  );
  const before = process.env.TZ;
  try {
    for (const { timezone, cases } of frozen.dates) {
      process.env.TZ = timezone;
      assert.equal(cases.length, 9);
      for (const { input, expected } of cases)
        assert.equal(shortDate(restore(input)), expected);
    }
  } finally {
    if (before === undefined) delete process.env.TZ;
    else process.env.TZ = before;
  }
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
