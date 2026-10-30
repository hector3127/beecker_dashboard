import test from "node:test";
import assert from "node:assert/strict";
import {
  csv,
  date,
  indicators,
  isWeekend,
  options,
  resourceDetail,
  selectedPeople,
  selectedRows,
} from "../../frontend/static/scripts/pages/capacity_daily/model.js";

const data = {
  mes: "2026-10",
  diasHabiles: 22,
  dias: ["2026-10-02", "2026-10-03"],
  personas: [
    { nombre: "Ana", rol: "Dev", banda: "B2", total: 200, facturables: 150 },
    { nombre: "Luis", rol: "QA", banda: "B1", total: 0, facturables: 0 },
  ],
  filas: [
    { nombre: "Ana", rol: "Dev", banda: "B2", idProyecto: "AER.001", proyecto: "Portal", dm: "Dora", clockifyId: "u1", facturables: 150, noFacturables: 50, total: 200, daily: { "2026-10-03": 4 } },
    { nombre: "Luis", rol: "QA", banda: "B1", idProyecto: "", proyecto: "", dm: "", clockifyId: "", facturables: 0, noFacturables: 0, total: 0, daily: {} },
  ],
};

test("indicators follow people x business days x workday", () => {
  const eight = indicators(data, 8);
  assert.equal(eight.base, 2 * 22 * 8);
  assert.equal(eight.balance, 352 - 200);
  assert.equal(eight.utilization, (200 / 352) * 100);
  assert.deepEqual([eight.people, eight.withHours, eight.over], [2, 1, 1]);
  assert.equal(indicators(data, 10).over, 0); // 220 h por persona
});

test("filters match name, project, manager and role/band", () => {
  const find = (extra) => selectedRows(data, { q: "", rol: "", banda: "", ...extra });
  assert.equal(find({}).length, 2);
  assert.deepEqual(find({ q: "dora" }).map((r) => r.nombre), ["Ana"]);
  assert.deepEqual(find({ q: "PORTAL" }).map((r) => r.nombre), ["Ana"]);
  assert.deepEqual(find({ rol: "QA" }).map((r) => r.nombre), ["Luis"]);
  assert.equal(find({ banda: "B9" }).length, 0);
  assert.equal(selectedPeople(data, { q: "luis", rol: "", banda: "" }).length, 1);
  assert.deepEqual(options(data, "rol"), ["Dev", "QA"]);
});

test("the CSV lists every day, escapes quotes and neutralises formulas", () => {
  const rows = [{ ...data.filas[0], proyecto: '=cmd|"x"' }];
  const lines = csv(data, rows).split("\r\n");
  assert.ok(lines[0].startsWith('﻿"Recurso","ID Clockify"'));
  assert.ok(lines[0].endsWith('"2026-10-02","2026-10-03"'));
  assert.ok(lines[1].includes("\"'=cmd|\"\"x\"\"\""));
  assert.ok(lines[1].endsWith('"","4"'));
});

test("person detail keeps every row, weekends are flagged and dates are short", () => {
  assert.equal(resourceDetail(data, "Ana").rows.length, 1);
  assert.equal(resourceDetail(data, "Nadie").person, undefined);
  assert.equal(isWeekend("2026-10-03"), true);
  assert.equal(isWeekend("2026-10-02"), false);
  assert.equal(date("2026-10-03"), "03/10");
  assert.equal(date(""), "—");
});
