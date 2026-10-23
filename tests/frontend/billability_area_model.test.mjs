import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  createModel,
  baseApply,
  baseSnapshot,
} from "../../frontend/static/scripts/pages/billability_area/model.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/facturabilidad_area.js",
  "utf8",
);
function previous() {
  const context = {
    window: {},
    document: { getElementById: () => ({ dataset: { year: "2026" } }) },
  };
  const end = source.lastIndexOf("\n})();");
  const hook = `globalThis.old={state,aggregate,workdays,kpis:gseKPIMetrics,resourceRows,bajas:gseBajaSet,baseApply,basePublish,
    filters(person,month){kpiPerson=person;kpiMonth=month;},
    silent(){render=()=>{};keepLoadedGSE=()=>{};}};`;
  vm.runInNewContext(source.slice(0, end) + hook + "\n})();", context);
  context.old.silent();
  return context.old;
}
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
  const old = previous(),
    a = job(),
    b = job();
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
    old.baseApply(a, batch);
    baseApply(b, batch);
    old.basePublish(a, 2);
    assert.deepEqual(plain(baseSnapshot(b, 2)), plain(old.state.data));
    assert.equal(b.seen.size, 3);
    assert.equal(b.invalid, a.invalid);
    assert.equal(b.unmatched, a.unmatched);
  }
  assert.throws(
    () => baseApply(b, { ok: false, error: "Falló Sheets" }),
    /Falló Sheets/,
  );
});

test("resource identities, bands, categories and KPI weights match the original model", () => {
  const old = previous(),
    batch = job();
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
  for (const area of ["", "DEV", "QA"])
    for (const day of [6, 8])
      for (const month of [-1, 1]) {
        Object.assign(state, { area, day });
        selection.kpiMonth = month;
        Object.assign(old.state, state);
        old.filters("", month);
        for (let i = 0; i < 12; i++) {
          assert.deepEqual(plain(model.aggregate(i)), plain(old.aggregate(i)));
          assert.equal(model.workdays(i), old.workdays(i));
        }
        assert.deepEqual(plain(model.kpis()), plain(old.kpis()));
        assert.deepEqual(
          plain(model.resourceRows()),
          plain(old.resourceRows()),
        );
        assert.deepEqual(plain(model.bajas()), plain(old.bajas()));
      }
  selection.kpiPerson = "ana perez";
  old.filters("ana perez", 1);
  assert.deepEqual(plain(model.kpis()), plain(old.kpis()));
});
