// Temporary explicit capture from the original, with no current model imports.
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const pick = (name) =>
  source.match(new RegExp(String.raw`  function ${name}\([\s\S]*?\n  \}`))[0];
const legacy = {};
for (const name of [
  "ixsRaidNumeroSeveridad",
  "ixsRaidNivel",
  "ixsRaidCerrado",
  "ixsRaidNormalizarSeveridad",
])
  vm.runInNewContext(pick(name), legacy);
const tag = (value) =>
  value === undefined ? { kind: "undefined" } : { kind: "value", value };
const values = [
  "1 - Crítico",
  "2",
  "3 – Bajo",
  "4",
  "5",
  "Very High",
  "Alto",
  "medium",
  "Bajo",
  "",
  null,
  undefined,
  "x",
].map((input) => ({
  input: tag(input),
  severity: tag(legacy.ixsRaidNumeroSeveridad(input)),
  level: tag(legacy.ixsRaidNivel(input)),
}));
const closed = [
  { estado: "closed" },
  { estado: "Active" },
  { cerrado: true },
  {},
  { estado: "Completed" },
].map((input) => ({ input, expected: legacy.ixsRaidCerrado(input) }));
const normalized = [
  { tipo: "Issue", severidad: "2 - Alto", probabilidad: "x" },
  { tipo: "Risk", severidad: "1", probabilidad: "y" },
  { tipo: "Risk", severidad: "" },
].map((input) => ({
  input,
  expected: JSON.parse(
    JSON.stringify(legacy.ixsRaidNormalizarSeveridad(structuredClone(input))),
  ),
}));
fs.writeFileSync(
  "tests/frontend/frozen/raid_severity.json",
  JSON.stringify({ values, closed, normalized }, null, 2) + "\n",
);
console.log(
  "Captured 13 severity/level pairs, 5 closed states and 3 normalized rows.",
);
