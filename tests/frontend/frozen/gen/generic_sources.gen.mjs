// Temporary original-only capture; run from repository root.
import fs from "node:fs";
import vm from "node:vm";
const original = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const format = vm.runInNewContext(
  "(" + original.match(/const fmtH = ([\s\S]*?\n    });/)[1] + ")",
);
const badge = vm.runInNewContext(
  "(" + original.match(/const badgeClass = ([\s\S]*?\n  });/)[1] + ")",
);
const hours = [
  null,
  undefined,
  "",
  0,
  -2,
  1.005,
  123456.789,
  "2.345",
  "invalid",
].map((value) => ({
  input: value === undefined ? { kind: "undefined" } : { kind: "value", value },
  expected: format(value),
}));
const badges = [
  null,
  "",
  "Alto",
  "MEDIO",
  "bajo",
  " Alto ",
  "unknown",
  "constructor",
  "__proto__",
].map((value) => ({ value, expected: badge(value) }));
fs.writeFileSync(
  "tests/frontend/frozen/generic_sources.json",
  JSON.stringify({ hours, badges }, null, 2) + "\n",
);
