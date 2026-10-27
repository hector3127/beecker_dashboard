import fs from "node:fs";
import vm from "node:vm";
// Explicit original-only capture, including original facts/context.
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const now = new Date("2026-10-23T18:00:00Z");
const scope = {
  window: {},
  aerIAEnsureStyles: () => {},
};
scope.Date = class extends Date {
  constructor(...args) {
    super(...(args.length ? args : [now]));
  }
};
vm.runInNewContext(source.match(/  function aerIAHoy[^\n]+/)[0], scope);
for (const name of ["aerIAContexto", "aerIAHechos"])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
for (const name of [
  "_aerEsc",
  "aerIAFechaMemoria",
  "aerIAFormatoResumen",
  "aerIAResumenDeUltimaMinuta",
])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
const start = source.indexOf("  function aerIAVista()");
vm.runInNewContext(
  source.slice(start, source.indexOf('    return `<div class="aeri">', start)) +
    "return {f,s,anal,mins,k,memoria,tz,resumen,recs,dim};\n}",
  scope,
);
const plain = (x) => JSON.parse(JSON.stringify(x));
const minutes = [
  "",
  "Sin encabezado <texto> & comillas ' \"",
  "**RESUMEN**\r\nAvance\r\n\r\n**PENDIENTES**\r\nAcciones",
  "## ESTADO GENERAL\nEstable\n⚠ PUNTOS DE ATENCIÓN\nPendiente",
  "**MINUTA proyecto**\n" + "Largo ".repeat(100),
].map((input) => ({
  input,
  expected: scope.aerIAResumenDeUltimaMinuta(input),
}));
const stamps = [
  null,
  "",
  "2026-10-22T14:30:00Z",
  "2026-10-22 14:30",
  " 22/10/2026 14:30 ",
].map((input) => ({ input, expected: scope.aerIAFechaMemoria(input) }));
const markup = [
  "***Título***\n\n**Avance:** estable\n- Revisar",
  "<script>alert(1)</script> &amp; <strong>Texto</strong>",
  "**texto & 'comillas'**\n• Uno\nDos",
  "***Título***\n \nNueva línea\n**sin cierre",
  "**<br>** y &bull; y &#039;",
  "***Anidado*** y **otro**",
].map((input) => ({ input, expected: scope.aerIAFormatoResumen(input) }));
const cases = [];
for (const consumoPct of [0, 90, 110, 250])
  for (const state of [
    { minutas: [] },
    {
      analisis: {
        analisis: { resumen: ["Guardado"], recomendaciones: [] },
        guardadoEn: "2026-10-22 14:30",
        restaurado: true,
      },
      minutas: [{ tema: "Comité" }],
    },
  ]) {
    const dashboard = { kpis: { consumoPct } };
    scope.aerDashboardData = structuredClone(dashboard);
    scope.aerIAState = structuredClone(state);
    cases.push({
      dashboard,
      state: plain(state),
      expected: plain(scope.aerIAVista()),
    });
  }
fs.writeFileSync(
  "tests/frontend/frozen/aer_ai_presentation.json",
  JSON.stringify({ minutes, stamps, markup, cases }, null, 2) + "\n",
);
console.log(
  "Captured",
  minutes.length,
  "excerpts,",
  stamps.length,
  "timestamps,",
  markup.length,
  "markup texts and",
  cases.length,
  "presentations.",
);
