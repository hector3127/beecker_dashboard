import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  executiveModel,
  timelineModel,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_executive_model.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
function original(name) {
  const line = source
    .split("\n")
    .find((line) => line.startsWith(`  function ${name}(`));
  return line.trim().endsWith("}")
    ? line
    : source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0];
}
const helperNames = [
  "_ixsNum",
  "_ixsPct",
  "_ixsLimit",
  "_ixsDate",
  "_ixsDateMs",
  "_ixsFases",
  "_ixsHitos",
  "_ixsFechaSalidaPRD",
  "nombreLimpioHito",
  "categoriaHito",
];
const helpers =
  "const EMOJI_REGEX = /\\p{Extended_Pictographic}/u;\n" +
  helperNames.map(original).join("\n");
const NativeDate = Date;
class FixedDate extends NativeDate {
  constructor(...args) {
    super(...(args.length ? args : ["2026-10-23T18:00:00Z"]));
  }
  static now() {
    return +new NativeDate("2026-10-23T18:00:00Z");
  }
}
const json = (value) => JSON.parse(JSON.stringify(value));
const samples = JSON.parse(
  fs.readFileSync("tests/ejecutivo/project_integrated_expected.json", "utf8"),
).slice(5, 12);

test("IXS executive preserves original thresholds, missing sources and presentation values", () => {
  const variants = [{}, ...samples];
  for (const fuente of [
    "Hitos principales",
    "Hitos y fechas de etapa",
    "Sin hitos planificados",
    "Consumo presupuestal",
  ]) {
    for (const indiceRitmo of [null, 0, 0.89, 0.9, 1.1, 1.11]) {
      const data = structuredClone(samples[0]);
      data.avance = {
        fuente,
        indiceRitmo,
        pct: 0,
        pctTiempoTranscurrido: 20,
        etapaActualPct: 0,
      };
      data.presupuesto.consumoDisponible = false;
      data.kpisExtra.pctCumplimientoFinanciero = indiceRitmo ? 130 : 0;
      data.proyecto.nivelRiesgoFecha = "Alto";
      variants.push(data);
    }
  }
  const keys = Object.keys(executiveModel({}));
  const calculation = original("_ixsRenderTab")
    .split("    const d=ixsProyectoActual,p=")[1]
    .split("    el.innerHTML=`")[0];
  try {
    globalThis.Date = FixedDate;
    for (const data of variants) {
      const snapshot = JSON.stringify(data);
      const context = { ixsProyectoActual: data, Date: FixedDate };
      vm.runInNewContext(
        helpers +
          "\nconst d=ixsProyectoActual,p=" +
          calculation +
          `\nglobalThis.observed={${keys.join(",")}};`,
        context,
      );
      assert.deepEqual(json(executiveModel(data)), json(context.observed));
      assert.equal(JSON.stringify(data), snapshot);
    }
  } finally {
    globalThis.Date = NativeDate;
  }
});

test("IXS timeline preserves phase matching, markers, suspensions and bounds", () => {
  const variants = [
    {},
    ...samples,
    {
      hitosAdicionales: [
        { tipo: "Demo", fecha: "2026-10-23" },
        { tipo: "UAT", fecha: "2026-10-23" },
        { tipo: "QA", fecha: "invalid" },
      ],
    },
  ];
  const busy = structuredClone(samples[0]);
  busy.suspensiones = [{ fechaInicio: "2026-09-01" }];
  busy.historialCompleto.push({
    ...busy.historialCompleto[0],
    fechaInicio: "2026-06-01",
  });
  variants.push(busy);
  const setup =
    original("_ixsGantt")
      .split("    const row=x=>")[0]
      .replace("  function _ixsGantt", "function oracle")
      .replace(
        "return '<div class=\"ixs-empty\">Sin fases disponibles en Historico_Proyectos.</div>';",
        "return null;",
      ) + "return {plan,real,holds,markers,loneMarkers,min,max,range,pos};}";
  try {
    globalThis.Date = FixedDate;
    for (const data of variants) {
      const context = { data, Date: FixedDate };
      vm.runInNewContext(
        helpers + setup + "\nglobalThis.observed=oracle(data);",
        context,
      );
      const actual = timelineModel(data),
        previous = context.observed;
      assert.deepEqual(json(actual), json(previous));
      if (actual)
        for (const date of ["2026-01-01", "2026-10-23", "2026-12-31"])
          assert.equal(actual.pos(date), previous.pos(date));
    }
  } finally {
    globalThis.Date = NativeDate;
  }
});
