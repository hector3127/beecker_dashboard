import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  computed,
  csv,
  days,
  selected,
} from "../../frontend/static/scripts/pages/capacity_daily/model.js";

const rule = {
  afecta: true,
  facturable: "Facturable",
  cargabilidad: "Cargable",
  capacidad: "Afecta Capacidad",
};
const row = (extra = {}) => ({
  recurso: "Ana Pérez",
  banda: "B1",
  concepto: "Proyecto",
  tecnologia: "DEV",
  manager: "DM",
  idProyecto: "P1",
  iteration: "",
  proyecto: "Portal",
  regla: rule,
  ...extra,
});
const state = (rows, meta = new Map()) => ({
  mes: "2026-10",
  jornada: 8,
  base: { filas: rows },
  meta,
  q: "",
  tecnologia: "",
  concepto: "",
});
const meta = {
  ok: true,
  inicio: "2026-10-01",
  fin: "2026-10-31",
  daily: { "ana perez": { "2026-10-01": 10, "2026-10-03": 7 } },
};

const reference = JSON.parse(
  fs.readFileSync(
    new URL("./snapshots/capacity_daily_model.json", import.meta.url),
    "utf8",
  ),
);

test("model retains the captured reference for known, pending, excluded and shared assignments", () => {
  const scenarios = [
    state([row()], new Map([["P1|", meta]])),
    state([row()]),
    state([row(), row({ concepto: "Sin Asignación" })]),
    state(
      [row(), row({ idProyecto: "P2", recurso: "Ana Perez" })],
      new Map([
        ["P1|", meta],
        ["P2|", { ...meta, daily: { "ana perez": { "2026-10-01": 4 } } }],
      ]),
    ),
    state(
      [row({ idProyecto: "" }), row({ idProyecto: "P2" })],
      new Map([["P2|", { ok: true, fueraMes: true }]]),
    ),
    state([row({ regla: null })], new Map([["P1|", meta]])),
    state(
      [row({ regla: { ...rule, afecta: false } })],
      new Map([["P1|", meta]]),
    ),
    state([row()], new Map([["P1|", { ok: false, error: "Sin conexión" }]])),
  ];
  assert.equal(reference.length, scenarios.length);
  scenarios.forEach((st, index) =>
    assert.deepEqual(
      JSON.parse(JSON.stringify(computed(st))),
      reference[index],
    ),
  );
});

test("weekends do not count and daily excess does not reduce availability on another day", () => {
  const result = computed(state([row()], new Map([["P1|", meta]])));
  assert.equal(days("2026-10").length, 22);
  assert.equal(result.people[0].total, 10);
  assert.equal(result.available, 168);
});

test("filters apply to CSV rows while the monthly totals stay unchanged", () => {
  const st = state(
    [row(), row({ recurso: "Luis", tecnologia: "QA", idProyecto: "" })],
    new Map([["P1|", meta]]),
  );
  st.q = "Pérez";
  const data = computed(st),
    rows = selected(data.all, st);
  assert.equal(data.people.length, 2);
  assert.equal(rows.length, 1);
  assert.match(csv(data, rows), /Ana Pérez/);
  assert.doesNotMatch(csv(data, rows), /Luis/);
  assert.match(csv(data, rows), /01\/10\/2026/);
});
