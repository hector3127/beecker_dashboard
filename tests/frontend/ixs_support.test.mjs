import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  suggestedDates,
  applyResourceStates,
  isoDate,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_support_model.js";
import { createIxsSupport } from "../../frontend/static/scripts/pages/project_detail/sections/ixs_support.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const original = {
  window: {},
  IXE_STAGES: ["Discovery", "Development", "Deployment"],
};
for (const name of ["_ixsDateMs", "_ixsFases", "_ixeAuto"])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    original,
  );
for (const name of ["_ixeIso", "_ixeStageOf"])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}[^\\n]+`))[0],
    original,
  );

for (const [label, data] of [
  ["empty", {}],
  [
    "planned",
    { hitos: [{ nombre: "Discovery EST", fechaFinPlan: "2010-03-20" }] },
  ],
  [
    "closed",
    {
      historialCompleto: [
        {
          fase: "Development",
          fechaInicio: "2010-01-01",
          fechaFin: "2010-03-02",
        },
      ],
      hitos: [{ nombre: "Development EST", fechaFinPlan: "2010-04-01" }],
    },
  ],
  [
    "active prefers planned close",
    {
      historialCompleto: [
        {
          fase: "Deployment",
          fechaInicio: "2010-01-01",
          fechaFin: "2010-03-02",
          enCurso: true,
        },
      ],
      hitos: [{ nombre: "Deployment EST", fechaFinPlan: "2010-04-01" }],
    },
  ],
  [
    "multiple cuts",
    {
      historialCompleto: [
        {
          fase: "Development",
          fechaInicio: "2010-01-01",
          fechaFin: "2010-02-02",
        },
        {
          fase: "Development",
          fechaInicio: "2010-02-01",
          fechaFin: "2010-03-01",
        },
        { fase: "Other", fechaInicio: "2010-04-01", fechaFin: "2010-05-01" },
      ],
    },
  ],
  [
    "Latin dates",
    {
      historialCompleto: [
        {
          fase: "DISCOVERY",
          fechaInicio: "01/02/2010",
          fechaFin: "28/02/2010",
        },
      ],
    },
  ],
]) {
  test(`suggested stage and close dates match previous: ${label}`, () => {
    assert.deepEqual(
      suggestedDates(data),
      JSON.parse(JSON.stringify(original._ixeAuto(data))),
    );
  });
}
test("resource matching preserves accents, duplicates, false and missing states", () => {
  const project = {
    filasRecursosCompleto: [
      { nombre: "  Ána  Pérez ", activo: true },
      { nombre: "Luis", activo: "unchanged" },
    ],
  };
  applyResourceStates(project, {
    filas: [
      { nombre: "Ana Perez", activo: true },
      { nombre: "ANA PEREZ", activo: false },
    ],
  });
  assert.equal(project.filasRecursosCompleto[0].activo, false);
  assert.equal(project.filasRecursosCompleto[1].activo, "unchanged");
  assert.equal(isoDate("bad"), "");
});
test("one resource read is shared in flight and retained after success", async () => {
  let resolve,
    calls = 0,
    paints = 0;
  const project = {
    proyecto: { id: "P" },
    filasRecursosCompleto: [{ nombre: "Ana" }],
  };
  const module = createIxsSupport(
    {
      resources: () => {
        calls++;
        return new Promise((done) => (resolve = done));
      },
    },
    { beeIxsPlanning: { paint: () => paints++ } },
  );
  const env = { project: () => project, tab: () => "planeacion" };
  const first = module.resources(env);
  await module.resources(env);
  assert.equal(calls, 1);
  resolve({ ok: true, filas: [{ nombre: "Ana", activo: false }] });
  await first;
  await module.resources(env);
  assert.equal(calls, 1);
  assert.equal(paints, 1);
  assert.equal(project._resourceStatesLoaded, true);
  assert.equal(project._resourceStatesLoading, false);
  assert.equal(project.filasRecursosCompleto[0].activo, false);
});
test("a late resource read fills its cached project without painting the new one", async () => {
  let resolve,
    paints = 0;
  const project = { proyecto: { id: "P" } };
  let current = project;
  const module = createIxsSupport(
    { resources: () => new Promise((done) => (resolve = done)) },
    { beeIxsPlanning: { paint: () => paints++ } },
  );
  const pending = module.resources({
    project: () => current,
    tab: () => "planeacion",
  });
  current = { proyecto: { id: "OTHER" } };
  resolve({ ok: true });
  await pending;
  assert.equal(project._resourceStatesLoaded, true);
  assert.equal(paints, 0);
  assert.equal(current._resourceStatesLoaded, undefined);
});
test("failed and unavailable reads release loading and allow a retry", async () => {
  let calls = 0;
  const project = { proyecto: { id: "P" } };
  const module = createIxsSupport(
    {
      resources: async () => {
        calls++;
        if (calls === 1) throw Error("offline");
        return { ok: calls > 2 };
      },
    },
    {},
  );
  const env = { project: () => project, tab: () => "ia" };
  for (let n = 0; n < 3; n++) await module.resources(env);
  assert.equal(calls, 3);
  assert.equal(project._resourceStatesLoading, false);
  assert.equal(project._resourceStatesLoaded, true);
});
test("timeline editing keeps the source index and date and only opens in planning", () => {
  const calls = [],
    project = {
      proyecto: { id: "P" },
      hitosAdicionales: [
        { tipo: "Demo", indice: 17, fecha: "28/02/2010", observacion: "note" },
      ],
    };
  let tab = "resumen";
  const env = {
    project: () => project,
    tab: () => tab,
    selectMilestones: (data) => calls.push(data),
    edit: (...args) => calls.push(args),
  };
  const module = createIxsSupport({}, {});
  module.editMilestone(0, env);
  tab = "planeacion";
  module.editMilestone(99, env);
  assert.equal(calls.length, 0);
  module.editMilestone(0, env);
  assert.equal(calls[0], project);
  assert.deepEqual(calls[1], ["Demo", 17, "2010-02-28", "note"]);
});
