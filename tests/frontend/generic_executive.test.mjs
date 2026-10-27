import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { genericExecutiveModel } from "../../frontend/static/scripts/pages/project_detail/sections/generic_executive_model.js";
import { createEntryRuntime } from "../../frontend/static/scripts/pages/project_detail/sections/project_entry_runtime.js";

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/generic_executive.json", import.meta.url),
    "utf8",
  ),
);
const json = (value) => JSON.parse(JSON.stringify(value));
const samples = frozen.samples,
  now = frozen.now;
function inZones(callback) {
  const previous = process.env.TZ;
  try {
    for (const zone of ["UTC", "America/Mexico_City"]) {
      process.env.TZ = zone;
      callback(frozen.cuts[zone]);
    }
  } finally {
    if (previous === undefined) delete process.env.TZ;
    else process.env.TZ = previous;
  }
}

test("generic context and completion assignments match the original renderer for all cuts", () => {
  assert.equal(samples.length, 7);
  inZones((cases) => {
    assert.equal(cases.length, 105);
    for (const { sampleIndex, service, status, expected } of cases) {
      const data = structuredClone(samples[sampleIndex]);
      data.proyecto.estadoGeneral = status;
      const metadata = { [data.proyecto.id]: { servicio: service } },
        before = json(data);
      const model = genericExecutiveModel(data, metadata, now);
      assert.deepEqual(json(model.context), expected.context);
      assert.deepEqual(
        { ...data.proyecto, ...model.projectPatch },
        expected.project,
      );
      assert.equal(model.milestones, data.hitosAdicionales);
      assert.deepEqual(json(model.milestones), expected.milestones);
      assert.deepEqual(json(data), before);
    }
  });
});

test("completed Deployment preserves exact override and does not alter source state until mount", () => {
  const data = structuredClone(samples[0]);
  data.proyecto.estadoGeneral = "EN RIESGO";
  data.proyecto.nivelRiesgoFecha = "Alto";
  data.hitos = [
    {
      nombre: "Deployment",
      fechaInicioPlan: "2026-07-01",
      fechaFinPlan: "2026-08-01",
    },
  ];
  data.historialCompleto = [
    { fase: "Deployment", fechaInicio: "2026-07-01", fechaFin: "2026-08-01" },
  ];
  data.suspensiones = [];
  const model = genericExecutiveModel(data, {}, now);
  assert.deepEqual(model.projectPatch, {
    estadoGeneral: "COMPLETADO",
    nivelRiesgoFecha: "Completado",
  });
  assert.equal(model.context.color, "#2E7D32");
  assert.equal(model.context.riskClass, "badge-bajo");
  assert.equal(data.proyecto.estadoGeneral, "EN RIESGO");
  assert.equal(model.summary.length, 1);
});

test("without planned milestones history alone never overrides completion; service metadata wins", () => {
  const data = structuredClone(samples[0]);
  data.hitos = [];
  delete data.hitosAdicionales;
  data.proyecto.servicio = "IXB";
  data.historialCompleto = [
    { fase: "Deployment", fechaInicio: "2026-07-01", fechaFin: "2026-08-01" },
  ];
  const model = genericExecutiveModel(
    data,
    { [data.proyecto.id]: { servicio: "CUSTOM" } },
    now,
  );
  assert.equal(model.timeline, null);
  assert.deepEqual(model.summary, []);
  assert.deepEqual(model.projectPatch, {});
  assert.equal(model.context.prd, false);
  assert.equal(model.context.prdDate, "");
  assert.deepEqual(model.milestones, []);
  assert.equal(
    genericExecutiveModel(data, {}, now).context.prdDate,
    "2026-08-01",
  );
});

test("service classification preserves word boundaries and original history/date precedence", () => {
  const data = structuredClone(samples[0]);
  data.hitos = [{ nombre: "Deployment EST", fechaFinPlan: "2027-12-01" }];
  data.historialCompleto = [
    { fase: "Deployment S2", fechaFin: "10/08/2026" },
    { fase: "Deployment", fechaFin: "2026-09-01" },
  ];
  assert.equal(frozen.services.length, 6);
  for (const { service, expected } of frozen.services) {
    data.proyecto.servicio = service;
    const model = genericExecutiveModel(data, {}, now);
    assert.equal(model.context.prd, expected.prd);
    assert.equal(model.context.prdDate, expected.prdDate);
  }
});

test("entry runtime uses direct generic service without consulting the old renderer", () => {
  const calls = [],
    data = { proyecto: { id: "GEN.001" } };
  const runtime = createEntryRuntime({
    contexts: { entry: (x) => x },
    executive: (value) => calls.push(value),
  }).connect({
    executive: () => {
      throw Error("old generic renderer");
    },
  });
  runtime.context().render.executive(data);
  assert.deepEqual(calls, [data]);
});
