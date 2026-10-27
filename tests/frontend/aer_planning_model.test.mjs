import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  planningModel,
  capacity,
  consumesCapacity,
  occupancy,
  resources,
  parsePlanText,
  normalizeImportDate,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_planning_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/aer_planning.json", import.meta.url),
    "utf8",
  ),
);
const plain = (value) => JSON.parse(JSON.stringify(value));
function inZones(callback) {
  const previous = process.env.TZ;
  try {
    for (const zone of ["UTC", "America/Mexico_City"]) {
      process.env.TZ = zone;
      callback(frozen[zone]);
    }
  } finally {
    if (previous === undefined) delete process.env.TZ;
    else process.env.TZ = previous;
  }
}

const pack = (v) =>
  v === undefined
    ? { kind: "undefined" }
    : typeof v === "number" && !Number.isFinite(v)
      ? { kind: String(v) }
      : { kind: "value", value: v };
const unpack = (v) => (v.kind === "undefined" ? undefined : v.value);
function atDate(callback) {
  const NativeDate = Date;
  try {
    globalThis.Date = class extends NativeDate {
      constructor(...args) {
        super(...(args.length ? args : [frozen.now]));
      }
    };
    callback();
  } finally {
    globalThis.Date = NativeDate;
  }
}
assert.equal(frozen.UTC.capacity.length, 3);
assert.equal(frozen.UTC.parsers.length, 8);
assert.equal(frozen.UTC.models.length, 9);
for (const [i, { name }] of frozen.UTC.capacity.entries()) {
  test(`Capacity and resources match original without mutation (${name})`, () =>
    inZones((group) => {
      const { dashboard, expected, consumes, capacities } = group.capacity[i];
      const before = plain(dashboard),
        rows = dashboard.plan.filas;
      assert.deepEqual(plain(resources(dashboard)), expected.resources);
      assert.deepEqual(plain(occupancy(rows, frozen.date)), expected.occupancy);
      assert.equal(consumes.length, rows.length + 1);
      for (const { row, expected: value } of consumes)
        assert.equal(consumesCapacity(row, frozen.date), value);
      assert.equal(capacities.length, 7);
      for (const { args, expected: value } of capacities)
        assert.deepEqual(plain(capacity(dashboard, ...args)), value);
      assert.deepEqual(dashboard, before);
    }));
}
for (const [i, { name }] of frozen.UTC.parsers.entries()) {
  test(`Import parser preserves original limitations (${name})`, () =>
    atDate(() =>
      inZones((group) => {
        const { text, project, expected } = group.parsers[i];
        const before = plain(project);
        assert.deepEqual(plain(parsePlanText(text, project)), expected);
        assert.deepEqual(project, before);
      }),
    ));
}
test("Imported dates use project year and retain unrecognized input", () =>
  inZones((group) => {
    assert.equal(group.dates.length, 18);
    for (const { project, value, expected } of group.dates) {
      assert.deepEqual(
        pack(normalizeImportDate(value, project, new Date(frozen.now))),
        expected,
      );
    }
  }));
for (const [i, { name, range }] of frozen.UTC.models.entries()) {
  test(`Planning summary and timeline match original (${name}, ${JSON.stringify(range)})`, () =>
    inZones((group) => {
      const { dashboard, range, expected, functions } = group.models[i];
      const before = plain({ dashboard, range });
      const actual = planningModel(dashboard, range, new Date(frozen.now));
      assert.deepEqual(plain(actual), expected);
      assert.equal(functions.length, actual.filas.length);
      for (const { row, state, dependency, width, dates } of functions) {
        assert.deepEqual(pack(actual.estadoCompromiso(row)), state);
        assert.deepEqual(pack(actual.depStatus(row)), dependency);
        assert.deepEqual(
          pack(actual.width(row.inicioPlan, row.finPlan)),
          width,
        );
        assert.equal(dates.length, 3);
        for (const { input, pos, short } of dates) {
          assert.deepEqual(pack(actual.pos(unpack(input))), pos);
          assert.deepEqual(pack(actual.fmtShort(unpack(input))), short);
        }
      }
      assert.deepEqual({ dashboard, range }, before);
    }));
}
