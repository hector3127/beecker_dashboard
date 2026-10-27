import fs from "node:fs";
import vm from "node:vm";
// Temporary explicit capture from the original, not current models.
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

const plain = (x) => JSON.parse(JSON.stringify(x));
const filters = [
  {},
  { status: "Active" },
  { person: "Ana", type: "To Be" },
  { query: "DESCRIPCIÓN" },
  { query: "demo final", status: "Closed" },
  { query: "ABC.001.003" },
  { query: "  Ana ", status: "Active" },
  { query: "descripcion" },
].map((input) => {
  values["ixs-azure-filter-estado"] = input.status;
  values["ixs-azure-filter-asignado"] = input.person;
  values["ixs-azure-filter-tipo"] = input.type;
  values["ixs-azure-filter-search"] = input.query;
  legacy.ixsAzureState = { items: structuredClone(rows) };
  return { input, expected: plain(legacy.ixsAzureApplyFilters()) };
});
const options = ["estado", "asignadoA", "tipo"].map((key) => ({
  key,
  expected: plain(legacy._ixsAzureUniqueOptions(rows, key)),
}));
const titles = [
  ...rows.map((x) => x.titulo),
  "ABC.001: Título",
  "abc.001.002 - Algo",
  "",
  null,
].map((input) => ({
  input,
  requirement: legacy._ixsAzureReq(input),
  title: legacy._ixsAzureTitleOnly(input),
}));
fs.writeFileSync(
  "tests/frontend/frozen/ixs_azure_table.json",
  JSON.stringify({ rows, filters, options, titles }, null, 2) + "\n",
);
console.log("Captured 8 filters, 3 option lists and 8 parsed titles.");
