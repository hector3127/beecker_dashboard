// Temporary explicit capture from the original; no current model imports.
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const pick = (name) =>
  source.match(new RegExp(String.raw`  function ${name}\([\s\S]*?\n  \}`))[0];
const plain = (value) => JSON.parse(JSON.stringify(value));
const tagged = (value) =>
  value === undefined ? { kind: "undefined" } : { kind: "value", value };
const save = (name, value) =>
  fs.writeFileSync(
    `tests/frontend/frozen/${name}.json`,
    JSON.stringify(value, null, 2) + "\n",
  );
const raid = {};
vm.runInNewContext(pick("ixsRaidPlanEnLineas"), raid);
save(
  "raid_plan_lines",
  [
    "",
    null,
    "• a • b ● c",
    "- uno\n* dos\n3) tres\n4. cuatro",
    "Una sola\r\nlinea",
    "1. x 2. y",
  ].map((input) => ({ input, expected: raid.ixsRaidPlanEnLineas(input) })),
);

const azure = { ixsAzureState: {} };
vm.runInNewContext(
  ["_ixsAz84Status", "_ixsAz84Stage", "_ixsAz84GroupData"].map(pick).join("\n"),
  azure,
);
const statuses = [
  " Active ",
  "In progress",
  "blocked",
  "CANCELLED",
  "Closed",
  "Not applicable",
  "Completed",
  "Inactive",
  "Rejected",
  "Proposed",
  "Risk",
  "",
  null,
].map((input) => ({ input, expected: azure._ixsAz84Status(input) }));
const stages = ["A\\Dev", "A\\QA\\", " ", "\\", null].map((input) => ({
  input,
  expected: tagged(azure._ixsAz84Stage(input)),
}));
const allItems = [
  "Active",
  "Closed",
  "Cancelled",
  "Blocked",
  "Proposed",
  "In progress",
  "Rejected",
  "Completed",
  "",
].map((estado, i) => ({
  id: i,
  estado,
  asignadoA: ["Ana", " Luis ", "", "Ana"][i % 4],
  iterationPath: ["A\\Dev", "B\\Dev", "A\\QA", ""][i % 4],
}));
const groups = [
  { allItems },
  { allItems: [] },
  {},
  { allItems: "invalid" },
].map((input) => {
  azure.ixsAzureState = structuredClone(input);
  return { input, expected: plain(azure._ixsAz84GroupData()) };
});
save("ixs_azure_groups", { statuses, stages, groups });

const badge = vm.runInNewContext("(" + pick("badgeEstadoClass") + ")");
const format = vm.runInNewContext("(" + pick("fmtFechaCorta") + ")");
const badges = [
  "Retrasado",
  "Excedido",
  "En riesgo",
  "En tiempo",
  "Sin estimacion en Recursos",
  "",
  null,
  undefined,
].map((input) => ({ input: tagged(input), expected: badge(input) }));
const before = process.env.TZ;
const dates = [];
const clockifyRanges = [];
try {
  for (const timezone of ["UTC", "America/Mexico_City"]) {
    process.env.TZ = timezone;
    dates.push({
      timezone,
      cases: [
        null,
        undefined,
        "",
        0,
        "bad",
        "2026-10-23",
        "2026-10-23T23:30:00Z",
        "2027-01-01T00:00:00Z",
        "23/10/2026",
      ].map((input) => ({ input: tagged(input), expected: format(input) })),
    });
    const valid = {
      ok: true,
      fechaInicio: "2026-08-01",
      fechaFin: "2026-10-23T12:00:00",
    };
    clockifyRanges.push({
      timezone,
      cases: [
        valid,
        { ...valid, fechaFin: null },
        { ...valid, fechaInicio: "invalid" },
      ].map((input) => ({
        input,
        expected: `Clockify: ${format(input.fechaInicio)} → ${format(input.fechaFin)}`,
      })),
    });
  }
} finally {
  if (before === undefined) delete process.env.TZ;
  else process.env.TZ = before;
}
save("generic_panel_helpers", { badges, dates });
save("project_clockify_range", clockifyRanges);
console.log(
  "Captured 6 RAID texts, 13 statuses, 5 stages, 4 groups, 8 badges and 18 dates.",
);
