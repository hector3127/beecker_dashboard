import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { createIxsAdapters } from "../../frontend/static/scripts/pages/project_detail/sections/project_ixs_adapters.js";
import {
  createProjectState,
  bindProjectState,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";
import { createProjectFeatureContexts } from "../../frontend/static/scripts/pages/project_detail/sections/project_feature_contexts.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const plain = (value) => JSON.parse(JSON.stringify(value));
function original(store) {
  const scope = { window: {} };
  bindProjectState(scope, store);
  vm.runInNewContext(source.match(/const EMOJI_REGEX[^\n]+/)[0], scope);
  for (const name of [
    "_ixsDateMs",
    "_ixsFases",
    "_ixsHitos",
    "nombreLimpioHito",
    "categoriaHito",
    "ixsIAContexto",
    "ixsIASnapshot",
    "ixsIACambios",
    "ixsIACapacidad",
  ])
    vm.runInNewContext(
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
      scope,
    );
  return scope;
}
for (const variant of ["empty", "milestones", "memory"])
  test(`${variant}: composed IA data matches original formulas and milestone preparation`, () => {
    const store = createProjectState();
    store.ixsAi.id = "P";
    if (variant !== "empty") {
      store.ixs = {
        proyecto: { id: "P", nombre: "Proyecto" },
        hitos: [
          {
            nombre: "Discovery",
            fechaInicioPlan: "2010-01-01",
            fechaFinPlan: "2010-02-01",
          },
        ],
        historialCompleto: [
          {
            fase: "Discovery",
            fechaInicio: "2010-01-02",
            fechaFin: "2010-02-05",
          },
        ],
        hitosAdicionales: [
          {
            tipo: "🎥 Demo <cliente>",
            fecha: "2010-01-20",
            indice: 7,
            observacion: "Notas",
          },
        ],
      };
      Object.assign(store.ixsAi, {
        azure: {
          allItems: [
            { id: 1, state: "Closed", assignedTo: { displayName: "Ana" } },
          ],
        },
        clockify: {
          registros: [{ recurso: "Ana", duracion: 2.5, fecha: "2010-01-01" }],
        },
        resources: {
          filas: [{ nombre: "Ana", horasEstimadas: 8, activo: true }],
        },
        plan: { compromisos: [], vacaciones: [] },
        cliente: { acciones: { filas: [] } },
      });
    }
    const adapter = createIxsAdapters(store, {}),
      old = original(store);
    if (variant === "memory") {
      const previous = plain(adapter.snapshot());
      previous.workItems[0].estado = "Active";
      previous.horas = 1;
      store.ixsAi.memoria = { actual: { snapshot: previous } };
    }
    for (const [key, name] of [
      ["context", "ixsIAContexto"],
      ["snapshot", "ixsIASnapshot"],
      ["changes", "ixsIACambios"],
      ["capacity", "ixsIACapacidad"],
    ])
      assert.deepEqual(plain(adapter[key]()), plain(old[name]()));
  });
test("timeline support opens the modular editor with the same project/index/reload", () => {
  const store = createProjectState(),
    calls = [],
    reload = () => {};
  const adapter = createIxsAdapters(store, {
    milestones: { edit: (...args) => calls.push(args) },
  });
  const context = adapter.support(reload);
  const project = { proyecto: { id: "P" }, hitosAdicionales: [{ indice: 17 }] };
  store.ixs = project;
  store.ixsTab = "planeacion";
  assert.equal(context.project(), project);
  assert.equal(context.tab(), "planeacion");
  context.selectMilestones(project);
  context.edit("Demo", 17, "2010-01-20", "Notas");
  assert.deepEqual(calls[0], [
    "P",
    project.hitosAdicionales,
    reload,
    { tipo: "Demo", indice: 17, fechaISO: "2010-01-20", observacion: "Notas" },
  ]);
});
for (const source of ["sources", "history", "drive"])
  test(`${source}: loading keeps the current state and original validity/paint hooks`, () => {
    const store = createProjectState(),
      paint = () => {},
      current = () => true;
    let call;
    const sources = {
      [source](...args) {
        assert.equal(this, sources);
        call = args;
        return "result";
      },
    };
    const adapter = createIxsAdapters(store, { sources, current });
    assert.equal(adapter.load(source, paint), "result");
    assert.equal(call[0], store.ixsAi);
    assert.equal(call[1].current, current);
    assert.equal(call[1].paint, paint);
  });
test("IA actions use modular models and retain the RAID handoff order", (t) => {
  const store = createProjectState();
  store.ixs = { proyecto: { id: "P" } };
  store.ixsAi.id = "P";
  const current = createProjectFeatureContexts(store).ixsCurrent;
  const adapter = createIxsAdapters(store, {
    current,
    controller: { actions: (state, env) => ({ state, env }) },
  });
  const calls = [],
    input = { value: "" },
    before = globalThis.document;
  globalThis.document = { getElementById: () => input };
  t.after(() => {
    globalThis.document = before;
  });
  const callbacks = {
    paint: () => {},
    tab: () => {},
    loadDrive: () => {},
    raidOpen: (type) => calls.push(type),
    raidManual: () => calls.push(input.value),
  };
  const bound = adapter.actions(callbacks);
  assert.equal(bound.state, store.ixsAi);
  assert.equal(bound.env.current(bound.state), true);
  assert.deepEqual(bound.env.context(), adapter.context());
  assert.deepEqual(bound.env.snapshot(), adapter.snapshot());
  bound.env.raid("Risk", "Texto <seguro>");
  assert.deepEqual(calls, ["Risk", "Texto <seguro>"]);
  store.ixsAi = { id: "OTHER" };
  assert.equal(bound.env.current(bound.state), false);
});

test("IA painting checks tab/project/state and uses its modular view", (t) => {
  const store = createProjectState(),
    calls = [],
    root = {};
  store.ixs = { proyecto: { id: "P" } };
  store.ixsAi.id = "P";
  let present = true;
  const before = globalThis.document;
  globalThis.document = { getElementById: () => (present ? root : null) };
  t.after(() => {
    globalThis.document = before;
  });
  const panels = () => {},
    adapter = createIxsAdapters(store, {
      current: () => true,
      controller: { actions: () => ({}) },
      panels,
      view: { render: (...args) => calls.push(args) },
    });
  adapter.paint({});
  assert.equal(calls.length, 0);
  store.ixsTab = "ia";
  adapter.paint({});
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], root);
  assert.equal(calls[0][1], store.ixsAi);
  assert.equal(calls[0][2].project, store.ixs);
  assert.equal(calls[0][2].panels, panels);
  store.ixsAi = { id: "OTHER" };
  adapter.paint({});
  assert.equal(calls.length, 1);
  present = false;
  adapter.paint({});
  assert.equal(calls.length, 1);
});
