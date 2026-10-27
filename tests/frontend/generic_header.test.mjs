import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { genericHeaderModel } from "../../frontend/static/scripts/pages/project_detail/sections/generic_header_model.js";
const base = () => ({
  proyecto: {
    id: "P",
    nombre: "Proyecto",
    cliente: "Cliente",
    estadoGeneral: "En progreso",
    nivelRiesgoFecha: "Alto",
  },
  avance: { pct: 43, indiceRitmo: 1, pctTiempoTranscurrido: 50 },
  presupuesto: { budget: 100, burn: 43, etc: 57, pctEjecutado: 43 },
});
const context = {
  color: "#2E7D32",
  riskClass: "badge-alto",
  prd: false,
  completed: false,
};
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/generic_header.json", import.meta.url),
    "utf8",
  ),
);

test("progress SVG geometry and raw rounded label retain the original helper behavior", () => {
  assert.equal(frozen.progress.length, 9);
  for (const { input, expected } of frozen.progress) {
    const pct =
      input.kind === "undefined"
        ? undefined
        : input.kind === "nan"
          ? NaN
          : input.value;
    const data = base();
    data.avance.pct = pct;
    const progress = genericHeaderModel(data, context).progress;
    assert.equal(`${progress.arc} ${progress.rest}`, expected.dash);
    assert.equal(progress.label, expected.label);
  }
});

test("pace threshold, missing value and completion keep the original texts", () => {
  for (const [value, completed, text, down] of [
    [null, false, "Sin fechas", false],
    [0, false, "En plan / eficiente", false],
    [1.1, false, "En plan / eficiente", false],
    [1.10001, false, "Por encima del plan", true],
    ["1.2", false, "Por encima del plan", true],
    [2, true, "Proyecto completado", false],
    [null, true, "Proyecto completado", false],
  ]) {
    const data = base();
    data.avance.indiceRitmo = value;
    const model = genericHeaderModel(data, { ...context, completed });
    assert.equal(model.paceText, text);
    assert.equal(model.paceDown, down);
    assert.equal(model.pace, value == null ? "—" : String(value));
  }
});

test("header and budget preserve defaults, raw numeric strings and missing financial fields", () => {
  const data = base(),
    before = structuredClone(data);
  const model = genericHeaderModel(data, context);
  assert.equal(model.project, "P - Proyecto");
  assert.equal(model.sponsor, "—");
  assert.equal(model.manager, "—");
  assert.equal(model.financial, "0%");
  assert.equal(model.planned, "Planificado: 50%");
  assert.deepEqual(data, before);
  data.kpisExtra = {};
  data.presupuesto.budget = "1234.50";
  assert.equal(genericHeaderModel(data, context).financial, "undefined%");
  assert.equal(genericHeaderModel(data, context).budget, "1234.50");
});

test("PRD and generic estimated exit keep their distinct placeholders and badge", () => {
  const data = base();
  assert.equal(genericHeaderModel(data, context).exitDate, "?");
  assert.equal(genericHeaderModel(data, context).exitClass, "badge badge-alto");
  const prd = genericHeaderModel(data, { ...context, prd: true });
  assert.equal(prd.exitDate, "—");
  assert.equal(prd.exitTitle, "Fecha de salida a PRD");
  assert.equal(prd.exitClass, "");
  assert.equal(prd.exitText, "Fin de Deployment");
});
