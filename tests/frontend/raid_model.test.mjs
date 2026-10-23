import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { filterRows, health, isClosed, level, matrix, normalizeSeverity, safeLink, severityNumber, stages } from "../../frontend/static/scripts/pages/project_detail/sections/raid_model.js";

const original = fs.readFileSync("apps/portal/static/portal/js/proyecto_detalle.js", "utf8");
const pick = (name) => original.match(new RegExp(String.raw`  function ${name}\([\s\S]*?\n  \}`))[0];
const legacy = {};
vm.runInNewContext(
  `${pick("ixsRaidNumeroSeveridad")}\n${pick("ixsRaidNivel")}\n${pick("ixsRaidCerrado")}\n${pick("ixsRaidNormalizarSeveridad")}\nthis.n=ixsRaidNumeroSeveridad;this.l=ixsRaidNivel;this.c=ixsRaidCerrado;this.s=ixsRaidNormalizarSeveridad;`,
  legacy,
);
const same = (a, b) => assert.equal(JSON.stringify(a), JSON.stringify(b));

test("severity, level and closed state match the original functions", () => {
  for (const v of ["1 - Crítico", "2", "3 – Bajo", "4", "5", "Very High", "Alto", "medium", "Bajo", "", null, undefined, "x"]) {
    assert.equal(severityNumber(v), legacy.n(v));
    assert.equal(level(v), legacy.l(v));
  }
  for (const row of [{ estado: "closed" }, { estado: "Active" }, { cerrado: true }, {}, { estado: "Completed" }]) assert.equal(isClosed(row), legacy.c(row));
  for (const row of [{ tipo: "Issue", severidad: "2 - Alto", probabilidad: "x" }, { tipo: "Risk", severidad: "1", probabilidad: "y" }, { tipo: "Risk", severidad: "" }]) same(normalizeSeverity(row), legacy.s(row));
});

test("health, matrix and stages count open records only", () => {
  const rows = [
    { tipo: "Risk", estado: "Active", impacto: "Alto", probabilidad: "Alto", iterationPath: "A\\Dev", diasSinActualizar: 9 },
    { tipo: "Issue", estado: "Closed", iterationPath: "A\\Dev" },
    { tipo: "Opportunity", estado: "Active", iterationPath: "" },
  ];
  const h = health(rows);
  same(h.counts.map((x) => x[1]), [1, 0, 1, 1]);
  assert.equal(h.stale, 1);
  assert.match(h.gradient, /^#ec4764 0% 33\.3/);
  assert.equal(matrix(rows).valid, 1);
  same(stages(rows).map((x) => [x.stage, x.total]), [["Dev", 1], ["Sin iteración", 1]]);
});

test("filters combine and links only point to Azure DevOps", () => {
  const rows = [
    { id: 1, tipo: "Risk", titulo: "Accesos", estado: "Active", asignadoA: "Ana", iterationPath: "A\\Dev" },
    { id: 2, tipo: "Issue", titulo: "Otro", estado: "Closed", asignadoA: "Luis", iterationPath: "A\\QA" },
  ];
  assert.equal(filterRows(rows, { tipo: "Risk", estado: "", persona: "", iter: "Dev", q: "ACCE" }).length, 1);
  assert.equal(filterRows(rows, { tipo: "", estado: "Closed", persona: "Ana", iter: "", q: "" }).length, 0);
  assert.equal(safeLink("https://dev.azure.com/o/p"), "https://dev.azure.com/o/p");
  assert.equal(safeLink("javascript:alert(1)"), "#");
});
