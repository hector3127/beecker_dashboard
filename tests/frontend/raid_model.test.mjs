import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  filterRows,
  health,
  isClosed,
  level,
  matrix,
  normalizeSeverity,
  safeLink,
  severityNumber,
  stages,
} from "../../frontend/static/scripts/pages/project_detail/sections/raid_model.js";

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/raid_severity.json", import.meta.url),
    "utf8",
  ),
);
const restore = (x) => (x.kind === "undefined" ? undefined : x.value);
const same = (a, b) => assert.equal(JSON.stringify(a), JSON.stringify(b));
test("severity, level and closed state match the original functions", () => {
  assert.equal(frozen.values.length, 13);
  assert.equal(frozen.closed.length, 5);
  assert.equal(frozen.normalized.length, 3);
  for (const row of frozen.values) {
    assert.equal(severityNumber(restore(row.input)), restore(row.severity));
    assert.equal(level(restore(row.input)), restore(row.level));
  }
  for (const { input, expected } of frozen.closed)
    assert.equal(isClosed(input), expected);
  for (const { input, expected } of frozen.normalized)
    same(normalizeSeverity(input), expected);
});

test("health, matrix and stages count open records only", () => {
  const rows = [
    {
      tipo: "Risk",
      estado: "Active",
      impacto: "Alto",
      probabilidad: "Alto",
      iterationPath: "A\\Dev",
      diasSinActualizar: 9,
    },
    { tipo: "Issue", estado: "Closed", iterationPath: "A\\Dev" },
    { tipo: "Opportunity", estado: "Active", iterationPath: "" },
  ];
  const h = health(rows);
  same(
    h.counts.map((x) => x[1]),
    [1, 0, 1, 1],
  );
  assert.equal(h.stale, 1);
  assert.match(h.gradient, /^#ec4764 0% 33\.3/);
  assert.equal(matrix(rows).valid, 1);
  same(
    stages(rows).map((x) => [x.stage, x.total]),
    [
      ["Dev", 1],
      ["Sin iteración", 1],
    ],
  );
});

test("filters combine and links only point to Azure DevOps", () => {
  const rows = [
    {
      id: 1,
      tipo: "Risk",
      titulo: "Accesos",
      estado: "Active",
      asignadoA: "Ana",
      iterationPath: "A\\Dev",
    },
    {
      id: 2,
      tipo: "Issue",
      titulo: "Otro",
      estado: "Closed",
      asignadoA: "Luis",
      iterationPath: "A\\QA",
    },
  ];
  assert.equal(
    filterRows(rows, {
      tipo: "Risk",
      estado: "",
      persona: "",
      iter: "Dev",
      q: "ACCE",
    }).length,
    1,
  );
  assert.equal(
    filterRows(rows, {
      tipo: "",
      estado: "Closed",
      persona: "Ana",
      iter: "",
      q: "",
    }).length,
    0,
  );
  assert.equal(
    safeLink("https://dev.azure.com/o/p"),
    "https://dev.azure.com/o/p",
  );
  assert.equal(safeLink("javascript:alert(1)"), "#");
});
