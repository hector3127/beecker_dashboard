// Temporary original-only capture. Remove with tests/reference after freezing.
// Run explicitly from repository root; never part of the test command.
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const plain = (value) => JSON.parse(JSON.stringify(value));
const start = source.indexOf("  function aerIAPreguntar()");
const normalized = source.indexOf("    const normalized=question", start);
const logic = source.slice(
  normalized,
  source.indexOf("    if(btn)", normalized),
);
const original = vm.runInNewContext(
  "question=>{" + logic + "return isSummary;}",
  {},
);
const questions = [
  "Resume el proyecto para comité",
  " RESUMEN EJECUTIVO ",
  "Resumen del estado",
  "¿Cuál es el riesgo?",
  "Puedes resume el proyecto para COMITÉ hoy",
  "resumen ejecutivo del cliente",
].map((input) => ({ input, expected: original(input) }));
const statement = source.match(
  /    const payload=\{ids:\(aerIAState.seleccion[^\n]+/,
)[0];
const payloads = [[], ["a"], ["1", "2", "3", "4", "5", "6"]].map(
  (seleccion) => {
    const input = { seleccion };
    const scope = { aerIAState: structuredClone(input) };
    vm.runInNewContext(statement + ";result=payload;", scope);
    return { input, expected: plain(scope.result) };
  },
);
fs.writeFileSync(
  "tests/frontend/frozen/aer_ai_actions_model.json",
  JSON.stringify({ questions, payloads }, null, 2) + "\n",
);

const scope = {
  window: {},
  Date: class extends Date {
    constructor(...args) {
      super(...(args.length ? args : ["2026-10-24T18:00:00Z"]));
    }
  },
};
for (const name of [
  "_aerNormFilter",
  "aerAplicarFiltrosPlan",
  "_aerInitPlanFiltroMes",
])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
vm.runInNewContext(source.match(/  function _aerMonthValue[^\n]+/)[0], scope);
const rows = [
  {
    tipo: "Actividad",
    actividad: "Revisión técnica",
    responsable: "Ana",
    estado: "Completado",
    compromiso: "2026-10-24",
    cierre: "2026-10-23",
  },
  {
    tipo: "Hito",
    actividad: "Entrega",
    responsable: "Sin responsable",
    estado: "Por validar",
    compromiso: "2026-10-25",
    cierre: "",
  },
  {
    tipo: "Actividad",
    actividad: "Diseño",
    responsable: "Beto",
    estado: "En progreso",
    compromiso: "",
    cierre: "",
  },
];
const filters = [
  {},
  { tipo: "Hito" },
  { actividad: "revision TECNICA" },
  { actividad: "ñ" },
  { responsable: "Ana" },
  { responsable: "ana" },
  { estado: "Por validar" },
  { compromisoDesde: "2026-10-24", compromisoHasta: "2026-10-24" },
  { cierreDesde: "2026-10-23", cierreHasta: "2026-10-23" },
  { compromisoDesde: "2026-10-25", compromisoHasta: "2026-10-24" },
  { actividad: "entrega", estado: "Completado" },
  { cierreDesde: "2026-10-24" },
].map((patch) => {
  const elements = rows.map((dataset) => ({ dataset, style: {} }));
  scope.aerPlanTableFilters = {
    tipo: "",
    actividad: "",
    responsable: "",
    compromisoDesde: "",
    compromisoHasta: "",
    estado: "",
    cierreDesde: "",
    cierreHasta: "",
    ...patch,
  };
  scope.document = {
    querySelectorAll: () => elements,
    getElementById: () => null,
  };
  scope.aerAplicarFiltrosPlan();
  return {
    patch,
    expected: elements.map((row) => row.style.display !== "none"),
  };
});
const ranges = [
  {},
  { desde: "2026-01", hasta: "" },
  { desde: "", hasta: "2026-12" },
  { desde: "2026-12", hasta: "2026-01" },
].map((input) => {
  scope.aerPlanFiltroMes = { ...input };
  scope._aerInitPlanFiltroMes();
  return { input, expected: plain(scope.aerPlanFiltroMes) };
});
fs.writeFileSync(
  "tests/frontend/frozen/aer_planning_filters.json",
  JSON.stringify({ rows, filters, ranges }, null, 2) + "\n",
);
console.log(
  "Captured original outputs: 6 questions, 3 payloads, 12 filters, 4 ranges",
);

const donut = vm.runInNewContext(
  "(" + source.match(/  function renderDonutMini\([\s\S]*?\n  \}/)[0] + ")",
);
const progress = [-15, 0, 43.5, 100, 120, null, "50", undefined, NaN].map(
  (pct) => {
    const html = donut(pct, "#4A2A94");
    return {
      input:
        pct === undefined
          ? { kind: "undefined" }
          : Number.isNaN(pct)
            ? { kind: "nan" }
            : { kind: "value", value: pct },
      expected: {
        dash: html.match(/stroke-dasharray="([^"]*)"/)[1],
        label: html.match(/<text[^>]*>([^<]*)<\/text>/)[1],
      },
    };
  },
);
fs.writeFileSync(
  "tests/frontend/frozen/generic_header.json",
  JSON.stringify({ progress }, null, 2) + "\n",
);
console.log("Captured 9 original progress SVG geometries and labels");
