import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  effortModel,
  activityRows,
  trendRows,
  excessByPerson,
  currentWeek,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_effort_model.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
function original(name) {
  const line = source
    .split("\n")
    .find((line) => line.startsWith(`  function ${name}(`));
  return line.trim().endsWith("}")
    ? line
    : source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0];
}
const helperNames = [
  "_ixsCalcEffort",
  "_ixsActividadRows",
  "_ixsTrendRows",
  "_ixsExcessByPerson",
  "_ixsRecursoClave",
  "_ixsYmdLocal",
  "_ixsSemanaActual",
];
const context = { Date };
vm.runInNewContext(helperNames.map(original).join("\n"), context);
const json = (value) => JSON.parse(JSON.stringify(value));

test("effort keeps original totals, zero fallbacks, nonbillable hours and rounding", () => {
  const samples = JSON.parse(
    fs.readFileSync("tests/ejecutivo/project_integrated_expected.json", "utf8"),
  ).slice(5, 12);
  const variants = [{}, ...samples];
  for (const value of [0, null, -2.1234, 17.99999]) {
    const d = structuredClone(samples[0]);
    d.totalesRecursos = {
      horasReales: value,
      horasNoFact: value,
      horasEstimadas: value,
      costoReal: value,
      pctCumplimientoFinanciero: value,
    };
    d.kpisExtra.horasFueraHorario = 2.5;
    variants.push(d);
  }
  for (const data of variants) {
    const snapshot = JSON.stringify(data);
    assert.deepEqual(
      json(effortModel(data)),
      json(context._ixsCalcEffort(data)),
    );
    assert.equal(JSON.stringify(data), snapshot);
  }
});

test("activities, trend and billable excess preserve grouping, chronology and deduplication", () => {
  const resources = [
    { nombre: "Ana Pérez", posicion: "Developer", horasEstimadas: 10 },
    { nombre: "Sin horas", horasEstimadas: 0 },
  ];
  const records = [
    {
      id: "2",
      recurso: "ANA PEREZ",
      fecha: "2026-10-03",
      inicio: "10:00",
      duracion: 8,
      billable: true,
      actividad: "Dev",
    },
    {
      id: "1",
      recurso: "Ana Pérez",
      fecha: "2026-10-01",
      inicio: "09:00",
      duracion: 8,
      billable: true,
      actividad: "Dev",
    },
    {
      id: "2",
      recurso: "ANA PEREZ",
      fecha: "2026-10-03",
      inicio: "10:00",
      duracion: 8,
      billable: true,
      actividad: "Dev",
    },
    { recurso: "Externo", fecha: "2026-09-01", duracion: 1.5, billable: true },
    {
      recurso: "Ana Pérez",
      fecha: "2026-08-01",
      duracion: 4,
      billable: false,
      actividad: "INV_OPERATIVA",
    },
    { recurso: "Ana Pérez", fecha: "invalid", duracion: -1, billable: true },
    { recurso: "Ana Pérez", fecha: "2026-07-01", duracion: 0, billable: true },
    {
      recurso: "Ana Pérez",
      fecha: "2026-06-01",
      duracion: 4,
      billable: "true",
    },
    {
      recurso: " ",
      fecha: "2026-05-01",
      duracion: 3,
      billable: true,
      actividad: " ",
    },
  ];
  for (const rows of [[], records, [...records].reverse()]) {
    const snapshot = JSON.stringify(rows);
    assert.deepEqual(
      json(activityRows(rows)),
      json(context._ixsActividadRows(rows)),
    );
    assert.deepEqual(json(trendRows(rows)), json(context._ixsTrendRows(rows)));
    assert.deepEqual(
      json(excessByPerson(resources, rows)),
      json(context._ixsExcessByPerson(resources, rows)),
    );
    assert.equal(JSON.stringify(rows), snapshot);
  }
  const ana = excessByPerson(resources, records).find(
    (x) => x.name === "Ana Pérez",
  );
  assert.equal(ana.excess, 6);
  assert.equal(ana.records.length, 1);
  assert.equal(ana.records[0].duracion, 8);
  assert.equal(ana.records[0].excess, 6);
});

test("default week preserves local Monday through Sunday across year boundaries", () => {
  const NativeDate = Date;
  try {
    for (const date of [
      "2026-10-23T18:00:00Z",
      "2026-10-25T18:00:00Z",
      "2026-10-26T18:00:00Z",
      "2027-01-01T18:00:00Z",
    ]) {
      class FixedDate extends NativeDate {
        constructor(...args) {
          super(...(args.length ? args : [date]));
        }
      }
      globalThis.Date = FixedDate;
      context.Date = FixedDate;
      assert.deepEqual(json(currentWeek()), json(context._ixsSemanaActual()));
    }
  } finally {
    globalThis.Date = NativeDate;
    context.Date = NativeDate;
  }
});

test("effort cache resets even when the intermediate project never opens Effort", async () => {
  const code = fs
    .readFileSync(
      "frontend/static/scripts/pages/project_detail/sections/ixs_effort.js",
      "utf8",
    )
    .replace(/import[\s\S]*?from "[^"]+";/g, "")
    .replace("export { effortResources };", "")
    .replace(
      "export function createEffortController",
      "function createEffortController",
    );
  const snapshots = [],
    pending = [];
  const api = {
    tasks: async () => ({ ok: true }),
    records: (id) => new Promise((resolve) => pending.push({ id, resolve })),
  };
  const sandbox = {
    document: { getElementById: () => null },
    currentWeek: () => ({ desde: "2026-10-19", hasta: "2026-10-25" }),
    renderEffort: () => {},
    effortResources: () => {},
    renderTasks: () => {},
    renderExcess: () => {},
    excessByPerson: () => [],
    renderClockify: (node, state) => snapshots.push(json(state)),
  };
  vm.runInNewContext(code, sandbox);
  const controller = sandbox.createEffortController(api),
    node = { isConnected: true, querySelector: () => ({}) },
    guards = { current: () => true, active: () => true };
  const a = { proyecto: { id: "A" } },
    b = { proyecto: { id: "B" } };
  controller.selectProject(a);
  controller.mount(node, a, guards);
  pending[0].resolve({
    ok: true,
    registros: [{ fecha: "2026-10-23", duracion: 8 }],
  });
  await new Promise((resolve) => setImmediate(resolve));
  controller.mount(node, a, guards);
  assert.equal(pending.length, 1);
  controller.selectProject(b);
  controller.selectProject(a);
  controller.mount(node, a, guards);
  assert.equal(pending.length, 2);
  controller.selectProject(b);
  controller.mount(node, b, guards);
  pending[1].resolve({
    ok: true,
    registros: [{ fecha: "2026-10-23", duracion: 999 }],
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(snapshots.at(-1).proyectoId, "B");
  assert.equal(snapshots.at(-1).registros, null);
  pending[2].resolve({
    ok: true,
    registros: [{ fecha: "2026-10-23", duracion: 4 }],
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(snapshots.at(-1).registros[0].duracion, 4);
});
