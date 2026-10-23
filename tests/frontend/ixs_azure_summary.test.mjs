import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const code = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const pick = (name) =>
  code.match(new RegExp(String.raw`  function ${name}\([\s\S]*?\n  \}`))[0];
const context = {
  window: {},
  document: { getElementById: () => null },
  _ixsAzureRenderSelect: () => {},
  _ixsAzureUniqueOptions: () => [],
};
const fields = [
  "total",
  "closed",
  "qa",
  "avg",
  "riskCount",
  "entries",
  "totalDist",
  "donut",
  "notes",
  "byAssigned",
  "maxOpen",
  "byDate",
];
vm.runInNewContext(
  [
    "_ixsAzureStatusClass",
    "_ixsAz84Status",
    "_ixsDateMs",
    "_ixsAzureReq",
    "_ixsAzureTitleOnly",
  ]
    .map(pick)
    .join("\n") +
    "\n" +
    pick("_ixsRenderAzureSummary").replace(
      /\n  }$/,
      `\n return {${fields.join(",")}};\n }`,
    ),
  context,
);
context.statusClass = context._ixsAzureStatusClass;
context.groupStatus = context._ixsAz84Status;
vm.runInNewContext(
  fs
    .readFileSync(
      "frontend/static/scripts/pages/project_detail/sections/ixs_azure_summary_model.js",
      "utf8",
    )
    .replace(/^import.*;$/gm, "")
    .replaceAll("export ", ""),
  context,
);
const rows = [
  "Active",
  "Closed",
  "Cancelled",
  "Blocked",
  "Proposed",
  "In progress",
  "Rejected",
  "Completed",
  "Risk",
].map((estado, i) => ({
  id: 100 + i,
  estado,
  titulo: `AMK.008 - Tarea ${i}`,
  tipo: i % 2 ? "To Be" : "Risk",
  asignadoA: i % 2 ? "Luis" : "Ana",
  avanceTotal: i * 17,
  qaListo: i % 2 === 0,
  fechaLimiteDev: i % 2 ? "2026-10-04" : "3/10/2026",
  diasSinActualizar: i * 3,
}));

for (const [name, state] of Object.entries({
  full: { items: rows.slice(0, 3), allItems: rows, stale: rows.slice(2) },
  empty: {},
  emptyAll: { items: rows, allItems: [], stale: [] },
  closed: { items: rows.filter((x) => x.estado === "Closed"), stale: [] },
})) {
  test(`summary equals original figures, distribution, ordering and dates: ${name}`, () => {
    context.ixsAzureState = structuredClone(state);
    const expected = context._ixsRenderAzureSummary();
    const before = JSON.stringify(state),
      actual = context.azureSummary(state);
    for (const field of fields)
      assert.equal(
        JSON.stringify(actual[field]),
        JSON.stringify(expected[field]),
        field,
      );
    assert.equal(JSON.stringify(state), before);
    assert.equal(
      actual.staleSorted.length,
      Math.min(8, (state.stale || []).length),
    );
  });
}

test("attention keeps top eight and average is not clamped by the model", () => {
  const state = {
    items: [{ avanceTotal: 150 }, { avanceTotal: -10 }],
    stale: Array.from({ length: 12 }, (_, i) => ({
      id: i,
      diasSinActualizar: i,
    })),
  };
  const value = context.azureSummary(state);
  assert.equal(value.avg, 70);
  assert.equal(value.staleCount, 12);
  assert.equal(value.staleSorted.length, 8);
  assert.equal(value.staleSorted[0].diasSinActualizar, 11);
});
