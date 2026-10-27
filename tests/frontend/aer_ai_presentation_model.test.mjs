import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  memoryDate,
  summaryMarkup,
  minuteSummary,
  presentation,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_ai_presentation_model.js";
import { facts } from "../../frontend/static/scripts/pages/project_detail/sections/aer_ai_model.js";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const now = new Date("2026-10-23T18:00:00Z");
const scope = {
  window: {},
  aerIAEnsureStyles: () => {},
  aerIAHechos: () => facts(scope.aerDashboardData, scope.aerIAState, now),
};
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
for (const contenido of [
  "",
  "Sin encabezado <texto> & comillas ' \"",
  "**RESUMEN**\r\nAvance\r\n\r\n**PENDIENTES**\r\nAcciones",
  "## ESTADO GENERAL\nEstable\n⚠ PUNTOS DE ATENCIÓN\nPendiente",
  "**MINUTA proyecto**\n" + "Largo ".repeat(100),
])
  test(`Minute excerpt matches original (${contenido.slice(0, 35)})`, () =>
    assert.equal(
      minuteSummary(contenido),
      scope.aerIAResumenDeUltimaMinuta(contenido),
    ));
test("Memory timestamps preserve Apps Script wall time without conversion", () => {
  for (const value of [
    null,
    "",
    "2026-10-22T14:30:00Z",
    "2026-10-22 14:30",
    " 22/10/2026 14:30 ",
  ])
    assert.equal(memoryDate(value), scope.aerIAFechaMemoria(value));
});
for (const value of [
  "***Título***\n\n**Avance:** estable\n- Revisar",
  "<script>alert(1)</script> &amp; <strong>Texto</strong>",
  "**texto & 'comillas'**\n• Uno\nDos",
  "***Título***\n \nNueva línea\n**sin cierre",
  "**<br>** y &bull; y &#039;",
  "***Anidado*** y **otro**",
])
  test(`Minimal summary markup retains original escaping (${value.slice(0, 25)})`, () =>
    assert.equal(summaryMarkup(value), scope.aerIAFormatoResumen(value)));
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
  ])
    test(`Presentation matches original (${consumoPct}/${!!state.analisis})`, () => {
      const dashboard = { kpis: { consumoPct } };
      scope.aerDashboardData = dashboard;
      scope.aerIAState = state;
      const before = JSON.stringify([dashboard, state]);
      assert.deepEqual(
        plain(presentation(dashboard, state, now)),
        plain(scope.aerIAVista()),
      );
      assert.equal(JSON.stringify([dashboard, state]), before);
    });
