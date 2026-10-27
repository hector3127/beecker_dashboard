// TEMPORAL: congela las salidas del original (tests/reference) para
// tests/frontend/aer_executive.test.mjs. Se borra junto con tests/reference.
// Uso: node tests/frontend/frozen/gen/aer_executive.gen.mjs
import fs from "node:fs";
import vm from "node:vm";
import { executiveModel } from "../../../../frontend/static/scripts/pages/project_detail/sections/aer_executive_model.js";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
function original(name) {
  const line = source
    .split("\n")
    .find((line) => line.startsWith(`  function ${name}(`));
  if (line.trim().endsWith("}")) return line;
  return source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0];
}
const date = new Date("2026-10-23T18:00:00Z");
const keys = Object.keys(executiveModel({}, date));
const oracle = original("_aerVistaEjecutivo").replace(
  'return `<div class="aer-exec-view">',
  `globalThis.observed = {${keys.join(",")}}; return \`<div class="aer-exec-view">`,
);
class FixedDate extends Date {
  constructor(...args) {
    super(...(args.length ? args : [date]));
  }
}
const json = (value) => JSON.parse(JSON.stringify(value));

const sample = JSON.parse(
  fs.readFileSync("tests/aer/aer_expected.json", "utf8"),
).results[3];
const variants = [
  {},
  sample,
  { proyecto: { fechaInicio: "2026-11-01", fechaFin: "2026-01-01" } },
];
for (const healthScore of [0, 69, 70, 84, 85, 100]) {
  for (const consumoPct of [0, 80, 100, 135]) {
    const data = structuredClone(sample);
    data.kpis = {
      healthScore,
      consumoPct,
      pctNoFacturables: 30,
      pctFueraHorario: 12,
      diasRestantes: -1,
    };
    data.plan = {
      filas: [
        { actividad: "Hoy", finPlan: "2026-10-23", estado: "Por validar", dependencia: "Acceso" },
        { actividad: "Tarde", finPlan: "2026-10-20", estado: "Detenida", dependencia: "ACCESO" },
        { actividad: "Próximo", finPlan: "2026-11-22", estado: "Abierto", dependencia: "Otro" },
        { actividad: "Cerrado", finPlan: "2026-10-22", finReal: "2026-10-21" },
        { actividad: "Pasado", finPlan: "2026-10-20", dependencia: "Acceso" },
      ],
      compromisosTotal: 0,
      pctCerrados: 0,
      pctCerradosATiempo: 0,
    };
    variants.push(data);
  }
}

const view = variants.map((input) => {
  const context = {
    aerDashboardData: input,
    Date: FixedDate,
    _aerEsc: (v) => String(v ?? ""),
    _aerBar: () => "",
  };
  vm.runInNewContext(
    ["_aerFmtH", "_aerFmtFecha", "_aerClamp", "_aerDimensionesDisponibles"]
      .map(original)
      .join("\n") +
      "\n" +
      oracle +
      "\n_aerVistaEjecutivo();",
    context,
  );
  return { input: json(input), expected: json(context.observed) };
});

const helpers = {};
vm.runInNewContext(
  ["_aerFmtH", "_aerFmtFecha", "_aerDimensionesDisponibles"]
    .map(original)
    .join("\n"),
  helpers,
);
const hourValues = [undefined, null, 0, 0.125, 1234.5678, -13.555];
const dateValues = [null, "", "2026-10-23T18:00:00Z", "Pendiente"];
const dimensionInputs = [
  {},
  { kpis: { healthDimensiones: { tiempo: 0, esfuerzo: 0, costo: 0, riesgo: 0 } } },
  { riesgos: { filas: [{}], score: 40 } },
  { kpis: { healthFuentes: { riesgo: true } } },
];
const formats = {
  hours: hourValues.map((value) => ({
    input: value === undefined ? "__undefined__" : value,
    expected: helpers._aerFmtH(value),
  })),
  dates: dateValues.map((value) => ({
    input: value,
    expected: helpers._aerFmtFecha(value),
  })),
  dimensions: dimensionInputs.map((input) => ({
    input,
    expected: json(helpers._aerDimensionesDisponibles(input)),
  })),
};

fs.writeFileSync(
  "tests/frontend/frozen/aer_executive.json",
  JSON.stringify({ view, formats }) + "\n",
);
console.log("congelados", view.length, "casos de vista");
