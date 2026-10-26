import test from "node:test";
import assert from "node:assert/strict";
import {
  computed,
  csv,
  selected,
} from "../../frontend/static/scripts/pages/capacity_daily/model.js";

function state() {
  return {
    mes: "2026-10",
    jornada: 8,
    q: "",
    tecnologia: "",
    concepto: "",
    base: {
      filas: [
        {
          recurso: "Ana",
          idProyecto: "P1",
          iteration: "",
          concepto: "Proyecto",
          regla: {
            afecta: true,
            facturable: "Facturable",
            cargabilidad: "Cargable",
          },
        },
      ],
    },
    meta: new Map([
      [
        "P1|",
        {
          ok: true,
          inicio: "2026-10-01",
          fin: "2026-10-31",
          daily: { ana: { "2026-10-01": 10 } },
        },
      ],
    ]),
  };
}

test("selected month and daily schedule retain base capacity and availability", () => {
  const st = state(),
    result = computed(st);
  assert.equal(result.days.length * st.jornada, 176);
  assert.equal(result.available, 168);
  assert.equal(result.people[0].total, 10);
  st.jornada = 6;
  assert.equal(computed(st).days.length * st.jornada, 132);
  assert.equal(computed(st).available, 126);
});

test("filtered CSV retains actual dates, project and hours without changing totals", () => {
  const st = state(),
    data = computed(st);
  const exported = csv(data, selected(data.all, st));
  assert.match(exported, /Ana/);
  assert.match(exported, /P1/);
  assert.match(exported, /01\/10\/2026/);
  assert.match(exported, /"10"/);
  st.q = "Sin coincidencia";
  assert.equal(selected(data.all, st).length, 0);
  assert.doesNotMatch(csv(data, selected(data.all, st)), /Ana|P1/);
  assert.equal(data.people[0].total, 10);
});
