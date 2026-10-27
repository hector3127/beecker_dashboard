import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  EMPTY_FILTERS,
  clientModel,
  contactsCsv,
  csvCell,
  initials,
  levelClass,
  linkTarget,
  normalize,
} from "../../frontend/static/scripts/pages/project_detail/sections/client_model.js";

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/client_helpers.json", import.meta.url),
    "utf8",
  ),
);

test("helpers match the original functions", () => {
  const cases = [
    ["levels", levelClass, 6],
    ["initials", initials, 5],
    ["csv", csvCell, 4],
    ["normalize", normalize, 3],
  ];
  for (const [name, fn, count] of cases) {
    assert.equal(frozen[name].length, count);
    for (const { input, expected } of frozen[name])
      assert.equal(fn(input), expected);
  }
});

const dashboard = {
  proyecto: { id: "P1", cliente: "ACME", deliveryManager: "Dora" },
  cliente: {
    contactos: [
      {
        uid: "1",
        nombre: "Ana",
        rol: "Sponsor",
        area: "TI",
        nivelDecision: "Alto",
        estado: "Activo",
        esDecisor: true,
        requerimientos: true,
        alcance: "Proyecto, Riesgos",
        canal: "Teams",
      },
      {
        uid: "2",
        nombre: "Luis",
        rol: "Usuario",
        area: "Ops",
        nivelDecision: "Bajo",
        estado: "Inactivo",
        informado: true,
        canal: "Correo",
      },
    ],
    info: { canales: "Teams, Correo" },
    gobierno: [],
    documentos: [
      { uid: "d", tipo: "Procedimiento" },
      { uid: "e", tipo: "Referencia" },
    ],
  },
};

test("the model derives the cards, filters and defaults", () => {
  const m = clientModel(dashboard, EMPTY_FILTERS, "aer");
  assert.deepEqual(
    m.kpis.map((k) => k[2]),
    [1, 1, 2, 2],
  );
  assert.deepEqual(
    m.key.map((x) => x.uid),
    ["1"],
  );
  assert.deepEqual(m.included, ["TI"]);
  assert.deepEqual(m.informed, ["Ops"]);
  assert.equal(m.governance.length, 3);
  assert.equal(m.governance[0].canal, "Teams");
  assert.equal(
    clientModel(dashboard, EMPTY_FILTERS, "ixs").governance.length,
    0,
  );
  assert.deepEqual(
    m.quickDocs.map((x) => x[2]),
    [1, 0, 1],
  );
  assert.equal(
    clientModel(dashboard, { ...EMPTY_FILTERS, q: "LÚIS" }, "aer").filtered
      .length,
    1,
  );
  assert.equal(
    clientModel(
      dashboard,
      { ...EMPTY_FILTERS, estado: "Activo", rol: "Usuario" },
      "aer",
    ).filtered.length,
    0,
  );
});

test("the CSV and links follow the previous rules", () => {
  const csv = contactsCsv(dashboard.cliente.contactos);
  assert.ok(csv.startsWith('﻿"Nombre","Cargo"'));
  assert.equal(csv.split("\r\n").length, 3);
  assert.equal(linkTarget("drive.google.com/x"), "https://drive.google.com/x");
  assert.equal(linkTarget("http://a.b"), "http://a.b");
  assert.equal(linkTarget("  "), "");
});
