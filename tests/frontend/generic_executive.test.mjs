import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { genericExecutiveModel } from "../../frontend/static/scripts/pages/project_detail/sections/generic_executive_model.js";
import { createEntryRuntime } from "../../frontend/static/scripts/pages/project_detail/sections/project_entry_runtime.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const begin = source.indexOf(
  "  function renderDashboardEjecutivoProyecto(data)",
);
const prefix = source.slice(
  source.indexOf("    const p = data.proyecto, av", begin),
  source.indexOf("    // ---- Gantt", begin),
);
const completion = source.slice(
  source.indexOf("    if (proyectoCompletadoDetectado)", begin),
  source.indexOf("    const ICONO_ESTADO_HITO", begin),
);
const helpers = ["_ixsDateMs", "_ixsFechaSalidaPRD"]
  .map(
    (name) =>
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
  )
  .join("\n");
const reference =
  vm.runInNewContext(`(data,mapaMetaProyectosDashboard,proyectoCompletadoDetectado)=>{
  ${helpers}
  const COLOR_ESTADO={verde:'#2E7D32',amarillo:'#F2A900',rojo:'#C62828',gris:'#8D8D91'};
  let hitosAdicionalesActuales,idProyectoActualGlobal;
  ${prefix}
  ${completion}
  return {context:{color:colorEstado,riskClass:riesgoFechaClase,
    prd:aplicaSalidaPRD,prdDate:fechaSalidaPRDLegacy,completed:proyectoCompletadoDetectado},
    project:data.proyecto,milestones:hitosAdicionalesActuales,id:idProyectoActualGlobal};
}`);
const json = (x) => JSON.parse(JSON.stringify(x));
const samples = JSON.parse(
  fs.readFileSync("tests/ejecutivo/project_integrated_expected.json", "utf8"),
).slice(5, 12);
const now = Date.parse("2026-10-23T18:00:00Z");

test("generic context and completion assignments match the original renderer for all cuts", () => {
  for (const sample of samples)
    for (const service of ["IXB", "RaaS", "SaaS", "CUSTOM", ""])
      for (const status of ["EN PROGRESO", "CERRADO", "CANCELADO"]) {
        const data = structuredClone(sample);
        data.proyecto.estadoGeneral = status;
        const metadata = { [data.proyecto.id]: { servicio: service } };
        const before = json(data),
          model = genericExecutiveModel(data, metadata, now);
        const expected = reference(
          structuredClone(data),
          metadata,
          !!model.timeline?.proyectoCompletadoDetectado,
        );
        assert.deepEqual(json(model.context), json(expected.context));
        assert.deepEqual(
          { ...data.proyecto, ...model.projectPatch },
          json(expected.project),
        );
        assert.equal(model.milestones, data.hitosAdicionales);
        assert.deepEqual(json(data), before);
      }
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
  for (const service of [
    "ixb",
    "IXB/SaaS",
    "xIXB",
    "CUSTOM",
    "RaaS",
    "SaaS extra",
  ]) {
    data.proyecto.servicio = service;
    const model = genericExecutiveModel(data, {}, now);
    const expected = reference(structuredClone(data), {}, false);
    assert.equal(model.context.prd, expected.context.prd);
    assert.equal(model.context.prdDate, expected.context.prdDate);
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
