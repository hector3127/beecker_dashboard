import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  hoursText,
  impactClass,
  tasksModel,
  raidModel,
} from "../../frontend/static/scripts/pages/project_detail/sections/generic_sources_model.js";

const original = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
test("task hours preserve original rounding, locale and missing values", () => {
  const format = vm.runInNewContext(
    "(" + original.match(/const fmtH = ([\s\S]*?\n    });/)[1] + ")",
  );
  for (const value of [
    null,
    undefined,
    "",
    0,
    -2,
    1.005,
    123456.789,
    "2.345",
    "invalid",
  ])
    assert.equal(hoursText(value), format(value));
});

test("risk badges preserve original mappings without normalization or deduplication", () => {
  const badge = vm.runInNewContext(
    "(" + original.match(/const badgeClass = ([\s\S]*?\n  });/)[1] + ")",
  );
  for (const value of [
    null,
    "",
    "Alto",
    "MEDIO",
    "bajo",
    " Alto ",
    "unknown",
    "constructor",
    "__proto__",
  ])
    assert.equal(impactClass(value), badge(value));
  const model = raidModel({
    riesgos: [
      {
        id: 1,
        descripcion: "Repeated",
        impacto: "Alto",
        severity: "Critical",
        estado: "Active",
        probabilidad: "Alta",
      },
      { id: 1 },
    ],
  });
  assert.equal(model.rows.length, 2);
  assert.deepEqual(model.rows[0], {
    description: "Repeated",
    detail: "#1 · Active · Severity: Critical",
    impact: "Alto",
    badge: "badge-alto",
    probability: "Alta",
  });
  assert.deepEqual(model.rows[1], {
    description: "",
    detail: "#1 · ",
    impact: "Medio",
    badge: "",
    probability: "—",
  });
  assert.deepEqual(model.totals, ["0", "0", "0"]);
});

test("task presentation keeps order, negative/zero disclosure and range truncation", () => {
  const input = {
    invOperativa: "2.25",
    invComercial: 3,
    totalHoras: 100,
    nomenclatura: "A.001",
    rango: { fechaInicio: "2026-01-01T23:00:00", fechaFin: "2026-10-23" },
    tasks: [
      { nombre: "B", horas: 2 },
      { horas: "1.234" },
      { nombre: "Negative", horas: -1 },
      { nombre: "Missing" },
      { nombre: "Invalid", horas: "bad" },
    ],
  };
  const snapshot = structuredClone(input),
    model = tasksModel(input);
  assert.deepEqual(model.withHours, [
    { name: "B", hours: "2 h" },
    { name: "Sin task", hours: "1.23 h" },
  ]);
  assert.deepEqual(model.withoutHours, ["Negative", "Missing"]);
  assert.equal(model.total, "100 h"); // Preserve server total; never sum rows.
  assert.equal(model.range, "Rango: 2026-01-01 → 2026-10-23 · Tasks activas");
  assert.equal(model.heading, "HORAS POR TASK · A.001");
  assert.deepEqual(input, snapshot);
  assert.equal(tasksModel({}).range, "");
});

const controllerSource = fs
  .readFileSync(
    "frontend/static/scripts/pages/project_detail/sections/generic_sources.js",
    "utf8",
  )
  .replace(/import[^;]+;/g, "")
  .replace("export function", "function");
const pending = () => {
  let resolve, reject;
  const promise = new Promise((a, b) => {
    resolve = a;
    reject = b;
  });
  return { promise, resolve, reject };
};

test("source controller protects replacement panels and newer totals from late responses", async () => {
  let target = {
    replaceChildren(...nodes) {
      this.nodes = nodes;
    },
  };
  const counts = Array.from({ length: 3 }, () => ({ textContent: "—" }));
  const queue = [pending(), pending(), pending()];
  let index = 0;
  const context = {
    taskNodes: (r) => [r],
    raidNode: (r) => r,
    sourceError: (t) => t,
    raidModel,
    document: {
      getElementById(id) {
        return id === "riesgos-criticos-proyecto-azure"
          ? target
          : counts[
              [
                "raid-proyecto-riesgos",
                "raid-proyecto-pendientes",
                "raid-proyecto-oportunidades",
              ].indexOf(id)
            ] || null;
      },
    },
  };
  vm.runInNewContext(controllerSource, context);
  const controller = context.createGenericSources({
    raid: () => queue[index++].promise,
  });
  const old = controller.raid("old"),
    newer = controller.raid("new");
  const result = { ok: true, totalRiesgos: 7 };
  queue[1].resolve(result);
  await newer;
  queue[0].reject(Error("late"));
  await old;
  assert.equal(target.nodes[0], result);
  assert.equal(counts[0].textContent, "7");
  const third = controller.raid("old");
  target = {
    replaceChildren() {
      throw Error("replacement touched");
    },
  };
  queue[2].resolve({ ok: true, totalRiesgos: 99 });
  await third;
  assert.equal(counts[0].textContent, "7");
});

test("failed sources keep totals and exact prefixes; missing target/project performs no read", async () => {
  const node = {
    replaceChildren(value) {
      this.value = value;
    },
  };
  let calls = 0;
  const context = {
    taskNodes: (r) => [r],
    raidNode: (r) => r,
    sourceError: (t) => t,
    raidModel,
    document: { getElementById: () => node },
  };
  vm.runInNewContext(controllerSource, context);
  const controller = context.createGenericSources({
    tasks: async () => {
      calls++;
      return { ok: false, error: "Unavailable" };
    },
    raid: async () => {
      throw Error("Network");
    },
  });
  await controller.tasks("");
  assert.equal(calls, 0);
  await controller.tasks("A");
  assert.equal(
    node.value,
    "No se pudieron cargar horas de Clockify: Unavailable",
  );
  await controller.raid("A");
  assert.equal(node.value, "Error cargando RAID de Azure: Network");
  const absent = context.createGenericSources(
    {
      tasks: () => {
        throw Error("unexpected read");
      },
    },
    { getElementById: () => null },
  );
  await absent.tasks("A");
});
