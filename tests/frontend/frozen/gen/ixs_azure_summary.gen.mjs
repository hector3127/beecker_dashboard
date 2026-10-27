// Temporary original-only capture, run explicitly from repository root.
const captured = [];
const test = (_name, callback) => callback();
import fs from "node:fs";
import vm from "node:vm";

const code = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
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
    captured.push({
      name,
      state,
      expected: JSON.parse(JSON.stringify(expected)),
    });
  });
}

fs.writeFileSync(
  "tests/frontend/frozen/ixs_azure_summary.json",
  JSON.stringify({ fields, cases: captured }, null, 2) + "\n",
);
