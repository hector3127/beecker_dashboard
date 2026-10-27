// Temporary original-only capture; run from repository root.
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const begin = source.indexOf(
  "  function renderDashboardEjecutivoProyecto(data)",
);
const prefix = source.slice(
  source.indexOf("    const p = data.proyecto, av", begin),
  source.indexOf("    // ---- Gantt", begin),
);
const completion = source.slice(
  source.indexOf("    if (proyectoCompletadoDetectado)", begin),
  source.indexOf("    const ICONO_ESTADO_HITO", begin),
);
const helpers = ["_ixsDateMs", "_ixsFechaSalidaPRD"]
  .map(
    (name) =>
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
  )
  .join("\n");
const reference =
  vm.runInNewContext(`(data,mapaMetaProyectosDashboard,proyectoCompletadoDetectado)=>{
  ${helpers}
  const COLOR_ESTADO={verde:'#2E7D32',amarillo:'#F2A900',rojo:'#C62828',gris:'#8D8D91'};
  let hitosAdicionalesActuales,idProyectoActualGlobal;
  ${prefix}
  ${completion}
  return {context:{color:colorEstado,riskClass:riesgoFechaClase,
    prd:aplicaSalidaPRD,prdDate:fechaSalidaPRDLegacy,completed:proyectoCompletadoDetectado},
    project:data.proyecto,milestones:hitosAdicionalesActuales,id:idProyectoActualGlobal};
}`);
const json = (x) => JSON.parse(JSON.stringify(x));
const samples = JSON.parse(
  fs.readFileSync("tests/ejecutivo/project_integrated_expected.json", "utf8"),
).slice(5, 12);
const now = Date.parse("2026-10-23T18:00:00Z");

const renderer = source.indexOf(
  "  function renderDashboardEjecutivoProyecto(data)",
);
const start = source.indexOf("      const marcadoresAdicionales =", renderer);
const end = source.indexOf("      return {filasPlan,", start);
if (!(start > renderer && end > start))
  throw Error("Missing original timeline");
const timelineHelpers = ["categoriaHito", "nombreLimpioHito"]
  .map(
    (name) =>
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
  )
  .join("\n");
const timelineReference = vm.runInNewContext(`(data, ahoraMs) => {
  const EMOJI_REGEX = /\\p{Extended_Pictographic}/u;
  ${timelineHelpers}
  const p=data.proyecto, msDia=86400000;
  const COLOR_TIPO={plan:'#C9C9CD',real:'#4A2A94',suspendido:'#F2A900',completado:'#2E7D32'};
  const historialCompleto=data.historialCompleto||[], suspensiones=data.suspensiones||[];
  const hitosResumenCorregido=[];
  let proyectoCompletadoDetectado=false;
  ${source.slice(start, end)}
  return {filasPlan,filasReal,marcadoresAdicionales,estadoEtapaReal,minT,maxT,rango,PAD_IZQ,meses,hitosResumenCorregido,proyectoCompletadoDetectado};
}`);

const captured = { samples, now, cuts: {}, services: [] };
const previousTZ = process.env.TZ;
try {
  for (const zone of ["UTC", "America/Mexico_City"]) {
    process.env.TZ = zone;
    const cuts = (captured.cuts[zone] = []);
    for (const [sampleIndex, sample] of samples.entries())
      for (const service of ["IXB", "RaaS", "SaaS", "CUSTOM", ""])
        for (const status of ["EN PROGRESO", "CERRADO", "CANCELADO"]) {
          const data = structuredClone(sample);
          data.proyecto.estadoGeneral = status;
          const metadata = { [data.proyecto.id]: { servicio: service } };
          const completed = !!(
            data.hitos &&
            data.hitos.length &&
            timelineReference(data, now).proyectoCompletadoDetectado
          );
          cuts.push({
            sampleIndex,
            service,
            status,
            expected: json(reference(data, metadata, completed)),
          });
        }
  }
} finally {
  if (previousTZ === undefined) delete process.env.TZ;
  else process.env.TZ = previousTZ;
}
const data = structuredClone(samples[0]);
data.hitos = [{ nombre: "Deployment EST", fechaFinPlan: "2027-12-01" }];
data.historialCompleto = [
  { fase: "Deployment S2", fechaFin: "10/08/2026" },
  { fase: "Deployment", fechaFin: "2026-09-01" },
];
for (const service of [
  "ixb",
  "IXB/SaaS",
  "xIXB",
  "CUSTOM",
  "RaaS",
  "SaaS extra",
]) {
  data.proyecto.servicio = service;
  captured.services.push({
    service,
    expected: json(reference(structuredClone(data), {}, false).context),
  });
}
fs.writeFileSync(
  "tests/frontend/frozen/generic_executive.json",
  JSON.stringify(captured, null, 2) + "\n",
);
