import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  filterWorkItems,
  workItemOptions,
  requirement,
  titleOnly,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_azure_table_model.js";

const original = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const pick = (name) =>
  original.match(new RegExp(String.raw`  function ${name}\([\s\S]*?\n  \}`))[0];
const values = {},
  legacy = {
    document: {
      getElementById: (id) =>
        id === "ixs-azure-table" ? {} : { value: values[id] || "" },
    },
  };
vm.runInNewContext(
  ["_ixsAzureReq", "_ixsAzureTitleOnly", "_ixsAzureUniqueOptions"]
    .map(pick)
    .join("\n") +
    "\n" +
    pick("ixsAzureApplyFilters").replace(
      "if(!filtered.length)",
      "return filtered; if(!filtered.length)",
    ),
  legacy,
);
const rows = [
  {
    id: 1,
    titulo: "AMK.008 - Descripción á",
    estado: "Active",
    asignadoA: "Ana",
    tipo: "To Be",
    demo: "Demo final",
  },
  {
    id: 2,
    titulo: "ABC.001.003 | Pruebas",
    estado: "Closed",
    asignadoA: "Luis",
    tipo: "Change Request",
  },
  {
    id: 3,
    titulo: "Sin código",
    estado: "Proposed",
    asignadoA: " Ana ",
    tipo: "To Be",
  },
  { id: 4, titulo: "XYZ.001_S1", estado: "Active", asignadoA: "Ana", tipo: "" },
];

test("filters match original exact selectors and combined case-insensitive search", () => {
  for (const filters of [
    {},
    { status: "Active" },
    { person: "Ana", type: "To Be" },
    { query: "DESCRIPCIÓN" },
    { query: "demo final", status: "Closed" },
    { query: "ABC.001.003" },
    { query: "  Ana ", status: "Active" },
    { query: "descripcion" },
  ]) {
    values["ixs-azure-filter-estado"] = filters.status;
    values["ixs-azure-filter-asignado"] = filters.person;
    values["ixs-azure-filter-tipo"] = filters.type;
    values["ixs-azure-filter-search"] = filters.query;
    legacy.ixsAzureState = { items: rows };
    const before = JSON.stringify(rows);
    assert.equal(
      JSON.stringify(filterWorkItems(rows, filters)),
      JSON.stringify(legacy.ixsAzureApplyFilters()),
    );
    assert.equal(JSON.stringify(rows), before);
  }
});

test("options, requirements and displayed titles keep the original parsing", () => {
  for (const key of ["estado", "asignadoA", "tipo"])
    assert.equal(
      JSON.stringify(workItemOptions(rows, key)),
      JSON.stringify(legacy._ixsAzureUniqueOptions(rows, key)),
    );
  for (const title of [
    ...rows.map((x) => x.titulo),
    "ABC.001: Título",
    "abc.001.002 - Algo",
    "",
    null,
  ]) {
    assert.equal(requirement(title), legacy._ixsAzureReq(title));
    assert.equal(titleOnly(title), legacy._ixsAzureTitleOnly(title));
  }
});
