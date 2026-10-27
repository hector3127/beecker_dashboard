// Temporary original-only capture. Run explicitly from repository root.

import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const renderer = source.indexOf(
  "  function renderDashboardEjecutivoProyecto(data)",
);
const start = source.indexOf("      const marcadoresAdicionales =", renderer);
const end = source.indexOf("      return {filasPlan,", start);
assert.ok(start > renderer && end > start);
const helpers = ["categoriaHito", "nombreLimpioHito"]
  .map(
    (name) =>
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
  )
  .join("\n");
const reference = vm.runInNewContext(`(data, ahoraMs) => {
  const EMOJI_REGEX = /\\p{Extended_Pictographic}/u;
  ${helpers}
  const p=data.proyecto, msDia=86400000;
  const COLOR_TIPO={plan:'#C9C9CD',real:'#4A2A94',suspendido:'#F2A900',completado:'#2E7D32'};
  const historialCompleto=data.historialCompleto||[], suspensiones=data.suspensiones||[];
  const hitosResumenCorregido=[];
  let proyectoCompletadoDetectado=false;
  ${source.slice(start, end)}
  return {filasPlan,filasReal,marcadoresAdicionales,estadoEtapaReal,minT,maxT,rango,PAD_IZQ,meses,hitosResumenCorregido,proyectoCompletadoDetectado};
}`);
const json = (value) => JSON.parse(JSON.stringify(value));
const comparable = (model) =>
  json({ ...model, states: model.filasReal.map(model.estadoEtapaReal) });
const samples = JSON.parse(
  fs.readFileSync("tests/ejecutivo/project_integrated_expected.json", "utf8"),
).slice(5, 12);

const captured = {};
const previousTZ = process.env.TZ;
try {
  for (const zone of ["UTC", "America/Mexico_City"]) {
    process.env.TZ = zone;
    const groups = (captured[zone] = { cuts: [], boundaries: [] });
    const test = (_name, callback) => callback();
    test("generic rows, scale, markers and completion match the untouched fallback for all cuts/states", () => {
      let cases = 0;
      for (const sample of samples)
        for (const estadoGeneral of ["EN PROGRESO", "CERRADO", "CANCELADO"]) {
          for (const date of [
            "2026-07-01T12:00:00Z",
            "2026-10-23T18:00:00Z",
            "2027-01-01T12:00:00Z",
          ]) {
            const data = structuredClone(sample);
            data.proyecto.estadoGeneral = estadoGeneral;
            const now = Date.parse(date);
            groups.cuts.push({
              data,
              now,
              expected: comparable(reference(data, now)),
            });
            cases++;
          }
        }
      assert.equal(cases, 63);
    });

    test("suspension boundaries, repeated phases, missing dates and marker categories retain their precedence", () => {
      const base = structuredClone(samples[0]);
      base.hitos = [
        {
          nombre: "Deployment",
          fechaInicioPlan: "2026-10-01",
          fechaFinPlan: "2026-10-23",
        },
      ];
      base.historialCompleto = [
        {
          fase: "Deployment",
          fechaInicio: "2026-10-01",
          fechaFin: "2026-10-10",
        },
        {
          fase: "deployment",
          fechaInicio: "2026-10-11",
          fechaFin: "2026-10-23",
        },
        { fase: "Missing", fechaInicio: null },
      ];
      base.hitosAdicionales = [
        "🎥 Demo final",
        "QA",
        "🚀 Producción",
        "Capacitación",
        "📌 Evento",
      ].map((tipo, indice) => ({
        tipo,
        indice,
        fecha: "23/10/2026",
        observacion: "Con 'comillas'",
      }));
      base.hitosAdicionales.push({ tipo: "Inválida", fecha: "sin fecha" });
      for (const from of ["2026-09-01", "2026-10-01", "2026-10-15", "bad"]) {
        for (const to of [null, "2026-10-10", "2026-10-23", "2026-11-01"]) {
          const data = {
            ...base,
            suspensiones: [{ fechaInicio: from, fechaFin: to }],
          };
          const now = Date.parse("2026-10-23T18:00:00Z");
          groups.boundaries.push({
            data,
            now,
            expected: comparable(reference(data, now)),
          });
        }
      }
    });
  }
} finally {
  if (previousTZ === undefined) delete process.env.TZ;
  else process.env.TZ = previousTZ;
}
fs.writeFileSync(
  "tests/frontend/frozen/generic_timeline.json",
  JSON.stringify(captured, null, 2) + "\n",
);
