import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  createModel,
  baseApply,
  baseSnapshot,
} from "../../frontend/static/scripts/pages/billability_area/model.js";

const reference = JSON.parse(
  fs.readFileSync(
    new URL("./snapshots/billability_area_model.json", import.meta.url),
    "utf8",
  ),
);
function plain(value) {
  return JSON.parse(
    JSON.stringify(value, (_, v) => {
      if (Object.prototype.toString.call(v) === "[object Set]") return [...v];
      if (Object.prototype.toString.call(v) === "[object Map]") return [...v];
      return v;
    }),
  );
}
function job() {
  return {
    year: 2026,
    area: "",
    seen: new Set(),
    months: {},
    invalid: 0,
    unmatched: 0,
    cursor: 0,
    total: null,
    done: false,
  };
}
const records = [
  {
    id: "1",
    mes: "2026-01",
    area: "DEV",
    recurso: "Ana Pérez",
    proyecto: "P1",
    banda: "Senior",
    categoria: "Facturable",
    tipo: "Facturable",
    servicio: "AER",
    categorias: ["Facturable"],
    horas: 84,
  },
  {
    id: "2",
    mes: "2026-02",
    area: "DEV",
    recurso: "Ana Pérez",
    proyecto: "P2",
    banda: "Baja",
    categoria: "Vacaciones",
    tipo: "No Facturables",
    servicio: "IxB",
    categorias: ["No Facturables", "Vacaciones"],
    horas: 20,
  },
  {
    id: "3",
    mes: "2026-02",
    area: "QA",
    recurso: "Eva",
    proyecto: "P3",
    banda: "Junior",
    categoria: "Inversión Comercial",
    tipo: "NA",
    servicio: "SaaS",
    categorias: ["Inversión Comercial"],
    horas: 42,
  },
];

test("annual batches preserve deduplication, partial months and unknown categories", () => {
  const b = job();
  for (const [index, warning] of ["", "Catálogo no disponible"].entries()) {
    const batch = {
      ok: true,
      records: [...records, records[0]],
      cursor: index ? 8 : 4,
      total: 8,
      done: Boolean(index),
      catalogoAviso: warning,
      bandas: [{ recurso: "Ana Pérez", bandas: ["Senior", "Baja"] }],
      invalid: 1,
      unmatched: 2,
    };
    baseApply(b, batch);
    assert.deepEqual(plain(baseSnapshot(b, 2)), reference.batches[index]);
    assert.equal(b.seen.size, 3);
    assert.equal(b.invalid, index + 1);
    assert.equal(b.unmatched, (index + 1) * 2);
  }
  assert.throws(
    () => baseApply(b, { ok: false, error: "Falló Sheets" }),
    /Falló Sheets/,
  );
});

test("resource identities, bands, categories and KPI weights match the original model", () => {
  const batch = job();
  baseApply(batch, {
    ok: true,
    records,
    done: true,
    cursor: 3,
    total: 3,
    bandas: [],
  });
  const data = baseSnapshot(batch, 3);
  const state = {
    year: 2026,
    day: 8,
    holidays: [1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1],
    area: "",
    data,
    resourceBands: [{ recurso: "Ana Pérez", bandas: ["Senior", "Baja"] }],
  };
  const selection = { kpiPerson: "", kpiMonth: -1 },
    model = createModel(state, selection);
  let variant = 0;
  for (const area of ["", "DEV", "QA"])
    for (const day of [6, 8])
      for (const month of [-1, 1]) {
        Object.assign(state, { area, day });
        selection.kpiMonth = month;
        for (let i = 0; i < 12; i++) {
          assert.deepEqual(
            plain(model.aggregate(i)),
            reference.aggregates[variant * 12 + i],
          );
          assert.equal(model.workdays(i), reference.workdays[variant * 12 + i]);
        }
        assert.deepEqual(plain(model.kpis()), reference.kpis[variant]);
        assert.deepEqual(
          plain(model.resourceRows()),
          reference.resources[variant],
        );
        assert.deepEqual(plain(model.bajas()), reference.bajas[variant]);
        variant++;
      }
  selection.kpiPerson = "ana perez";
  assert.equal(variant, 12);
  assert.equal(reference.kpis.length, 13);
  assert.equal(reference.aggregates.length, 144);
  assert.deepEqual(plain(model.kpis()), reference.kpis[variant]);
});
