import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { EMPTY_FILTERS, clientModel, contactsCsv, csvCell, initials, levelClass, linkTarget, normalize } from "../../frontend/static/scripts/pages/project_detail/sections/client_model.js";

const original = fs.readFileSync("tests/reference/static/portal/js/proyecto_detalle.js", "utf8");
const pick = (name) => original.match(new RegExp(String.raw`  function ${name}\([\s\S]*?\n  \}`))[0];
const legacy = {};
vm.runInNewContext(
  `${pick("_aerClienteNivelClase")}\n${pick("_aerClienteInitials")}\n${pick("_aerClienteCsv")}\n${pick("_aerNormFilter")}\nthis.l=_aerClienteNivelClase;this.i=_aerClienteInitials;this.c=_aerClienteCsv;this.n=_aerNormFilter;`,
  legacy,
);

test("helpers match the original functions", () => {
  for (const v of ["Alto", "medio", "Bajo", "", null, "x"]) assert.equal(levelClass(v), legacy.l(v));
  for (const v of ["Ana Pérez", "  luis  soto gil ", "", null, "x"]) assert.equal(initials(v), legacy.i(v));
  for (const v of ['a"b', null, 12, "x,y"]) assert.equal(csvCell(v), legacy.c(v));
  for (const v of ["ÁÉÍ  Ñu ", null, "Hola"]) assert.equal(normalize(v), legacy.n(v));
});

const dashboard = {
  proyecto: { id: "P1", cliente: "ACME", deliveryManager: "Dora" },
  cliente: {
    contactos: [
      { uid: "1", nombre: "Ana", rol: "Sponsor", area: "TI", nivelDecision: "Alto", estado: "Activo", esDecisor: true, requerimientos: true, alcance: "Proyecto, Riesgos", canal: "Teams" },
      { uid: "2", nombre: "Luis", rol: "Usuario", area: "Ops", nivelDecision: "Bajo", estado: "Inactivo", informado: true, canal: "Correo" },
    ],
    info: { canales: "Teams, Correo" },
    gobierno: [],
    documentos: [{ uid: "d", tipo: "Procedimiento" }, { uid: "e", tipo: "Referencia" }],
  },
};

test("the model derives the cards, filters and defaults", () => {
  const m = clientModel(dashboard, EMPTY_FILTERS, "aer");
  assert.deepEqual(m.kpis.map((k) => k[2]), [1, 1, 2, 2]);
  assert.deepEqual(m.key.map((x) => x.uid), ["1"]);
  assert.deepEqual(m.included, ["TI"]);
  assert.deepEqual(m.informed, ["Ops"]);
  assert.equal(m.governance.length, 3);
  assert.equal(m.governance[0].canal, "Teams");
  assert.equal(clientModel(dashboard, EMPTY_FILTERS, "ixs").governance.length, 0);
  assert.deepEqual(m.quickDocs.map((x) => x[2]), [1, 0, 1]);
  assert.equal(clientModel(dashboard, { ...EMPTY_FILTERS, q: "LÚIS" }, "aer").filtered.length, 1);
  assert.equal(clientModel(dashboard, { ...EMPTY_FILTERS, estado: "Activo", rol: "Usuario" }, "aer").filtered.length, 0);
});

test("the CSV and links follow the previous rules", () => {
  const csv = contactsCsv(dashboard.cliente.contactos);
  assert.ok(csv.startsWith('﻿"Nombre","Cargo"'));
  assert.equal(csv.split("\r\n").length, 3);
  assert.equal(linkTarget("drive.google.com/x"), "https://drive.google.com/x");
  assert.equal(linkTarget("http://a.b"), "http://a.b");
  assert.equal(linkTarget("  "), "");
});
