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
const frozen = JSON.parse(
  fs.readFileSync(new URL("./frozen/ixs_effort.json", import.meta.url), "utf8"),
);
const plain = (value) => JSON.parse(JSON.stringify(value));
const json = plain;
test("effort keeps original totals, zero fallbacks, nonbillable hours and rounding", () => {
  assert.equal(frozen.totals.length, 12);
  for (const { data, expected } of frozen.totals) {
    const before = plain(data);
    assert.deepEqual(plain(effortModel(data)), expected);
    assert.deepEqual(data, before);
  }
});
test("activities, trend and billable excess preserve grouping, chronology and deduplication", () => {
  assert.equal(frozen.rows.length, 3);
  for (const { resources, input, expected } of frozen.rows) {
    const before = plain({ resources, input });
    assert.deepEqual(plain(activityRows(input)), expected.activities);
    assert.deepEqual(plain(trendRows(input)), expected.trend);
    assert.deepEqual(plain(excessByPerson(resources, input)), expected.excess);
    assert.deepEqual({ resources, input }, before);
  }
  const { resources, input } = frozen.rows[1];
  const ana = excessByPerson(resources, input).find(
    (x) => x.name === "Ana Pérez",
  );
  assert.equal(ana.excess, 6);
  assert.equal(ana.records.length, 1);
  assert.equal(ana.records[0].duracion, 8);
  assert.equal(ana.records[0].excess, 6);
});
test("default week preserves local Monday through Sunday across year boundaries", () => {
  assert.equal(frozen.weeks.length, 4);
  const NativeDate = Date;
  try {
    for (const { date, expected } of frozen.weeks) {
      globalThis.Date = class extends NativeDate {
        constructor(...args) {
          super(...(args.length ? args : [date]));
        }
      };
      assert.deepEqual(plain(currentWeek()), expected);
    }
  } finally {
    globalThis.Date = NativeDate;
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
