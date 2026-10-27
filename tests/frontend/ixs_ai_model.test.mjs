import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const names = [
  "ixsIAContexto",
  "ixsIASnapshot",
  "ixsIACambios",
  "ixsIACapacidad",
];
const old = { window: {}, _ixsHitos: () => milestones };
vm.runInNewContext(
  names
    .map(
      (name) =>
        source.match(
          new RegExp(`  function ${name}\\(\\)\\{[\\s\\S]*?\\n  \\}`),
        )[0],
    )
    .join("\n"),
  old,
);
const modern = {};
vm.runInNewContext(
  fs
    .readFileSync(
      "frontend/static/scripts/pages/project_detail/sections/ixs_ai_model.js",
      "utf8",
    )
    .replaceAll("export ", ""),
  modern,
);
const plain = (value) => JSON.parse(JSON.stringify(value));
const milestones = [
  {
    name: "Entrega",
    start: "2026-10-01",
    finish: "2026-10-23",
    state: "Active",
    group: "Etapa",
    notes: "Seguimiento",
  },
];
const project = {
  proyecto: { nombre: "Proyecto", fechaCorte: "2026-10-23", etapa: "Entrega" },
  avance: { real: 50 },
  presupuesto: { horas: 100 },
};
const full = {
  id: "ABC.001",
  sourceErrors: { plan: "No disponible" },
  azure: {
    allItems: [
      {
        id: 1,
        state: "Closed",
        assignedTo: { displayName: "Ana" },
        iterationPath: "Sprint 1",
      },
      { id: 2, estado: "Active", asignado: "Luis" },
      {
        id: 3,
        state: "Resolved",
        assignedTo: { uniqueName: "ana@example.com" },
      },
    ],
    stale: [1],
  },
  clockify: {
    registros: [
      {
        recurso: " Ana Pérez ",
        duracion: "2.345",
        fecha: "2026-10-21T12:00:00",
      },
      { recurso: "ANA PEREZ", duracion: 3, fecha: "2026-10-21" },
      { nombre: "Luis", duracion: 4, fecha: "2026-10-22" },
      { recurso: "Ana Pérez", duracion: -1 },
      { recurso: "Ana Pérez", duracion: "invalid" },
      { duracion: 2, fecha: "2026-10-22" },
    ],
  },
  resources: {
    filas: [
      { nombre: "Ana Pérez", horasEstimadas: "20" },
      { nombre: "Luis", horasEstimadas: 8, activo: false },
    ],
  },
  plan: { compromisos: [{ uid: "c1" }], vacaciones: [{ nombre: "Ana" }] },
  raid: { registros: [{ id: 1 }, { id: 2 }] },
  cliente: { acciones: { filas: [{ uid: "a1", estado: "Completada" }] } },
  minutas: Array.from({ length: 4 }, (_, i) => ({
    fecha: String(i),
    tema: "Tema",
    contenido: "x".repeat(1500),
  })),
  memoria: {
    actual: {
      fecha: "2026-10-20",
      analisis: { resumen: "Previo" },
      snapshot: {
        fuentes: ["azure", "clockify"],
        workItems: [
          { id: "1", estado: "Active" },
          { id: "2", estado: "Active" },
        ],
        horas: 4,
        raidIds: ["1"],
        acciones: [{ uid: "a1", estado: "Pendiente" }],
      },
    },
  },
};

function compare(state) {
  const before = JSON.stringify(state);
  old.ixsIAState = state;
  old.ixsProyectoActual = project;
  const context = modern.context(state, project, milestones);
  assert.deepEqual(plain(context), plain(old.ixsIAContexto()));
  const snapshot = modern.snapshot(state, context);
  assert.deepEqual(plain(snapshot), plain(old.ixsIASnapshot()));
  assert.deepEqual(
    plain(modern.changes(state, () => snapshot)),
    plain(old.ixsIACambios()),
  );
  assert.deepEqual(plain(modern.capacity(state)), plain(old.ixsIACapacidad()));
  assert.equal(JSON.stringify(state), before);
  return { context, snapshot };
}

test("IA preserves original context, snapshots, changes and capacity with full data", () => {
  const { context, snapshot } = compare(structuredClone(full));
  assert.equal(context.minutas.length, 3);
  assert.equal(context.minutas[0].contenido.length, 1200);
  // These intentionally differ: context excludes negative/unnamed hours;
  // snapshot keeps the original sum of every valid duration.
  assert.equal(context.horasClockifyTotal, 9.35);
  assert.equal(snapshot.horas, 10.35);
});
test("IA preserves empty sources and no previous snapshot", () => {
  compare({ id: "EMPTY", sourceErrors: {}, minutas: [] });
});
test("IA preserves incomplete comparisons and partial source availability", () => {
  const state = structuredClone(full);
  delete state.azure;
  compare(state);
  state.azure = full.azure;
  state.memoria.actual.snapshot.fuentes = ["azure"];
  compare(state);
});
test("IA keeps the previous lazy snapshot behavior when no memory exists", () => {
  assert.equal(
    modern.changes({}, () => {
      throw Error("unexpected snapshot");
    }),
    null,
  );
});
