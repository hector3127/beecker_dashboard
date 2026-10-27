// Temporary original-only capture; run from repository root.

import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const scope = {
  window: {},
  Date: class extends Date {
    constructor(...args) {
      super(...(args.length ? args : ["2026-10-23T18:00:00Z"]));
    }
  },
};
for (const name of [
  "_aerRecursosProyecto",
  "_aerFilaConsumeCapacidad",
  "_aerOcupacionActualPorResponsable",
  "_aerMaxCapacidadEnRango",
  "_aerNormalizarFechaImport",
  "_aerParseDelimitedLine",
  "_aerParsePlanText",
]) {
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
}
vm.runInNewContext(
  "function _aerTodayIso(){return new Date().toISOString().slice(0,10);}",
  scope,
);
const plain = (x) => JSON.parse(JSON.stringify(x));
const date = "2026-10-23";
const data = JSON.parse(fs.readFileSync("tests/aer/aer_expected.json", "utf8"))
  .results[3];

const captured = {};
const pack = (v) =>
  v === undefined
    ? { kind: "undefined" }
    : typeof v === "number" && !Number.isFinite(v)
      ? { kind: String(v) }
      : { kind: "value", value: v };
const previousTZ = process.env.TZ;
try {
  for (const zone of ["UTC", "America/Mexico_City"]) {
    process.env.TZ = zone;
    const group = (captured[zone] = {
      capacity: [],
      parsers: [],
      dates: [],
      models: [],
    });
    const test = (_name, callback) => callback();
    for (const [name, rows] of [
      ["original", data.plan.filas],
      ["empty", []],
      [
        "boundaries",
        [
          {
            uid: "past",
            responsable: "Ana",
            tipo: "Actividad",
            estado: "En progreso",
            inicioPlan: "2026-09-01",
            finPlan: "2026-10-01",
            esfuerzo: 5,
          },
          {
            uid: "future",
            responsable: "Ana",
            tipo: "Actividad",
            estado: "Por iniciar",
            inicioPlan: "2026-11-01",
            finPlan: "2026-11-10",
            orden: 4,
          },
          {
            uid: "closed",
            responsable: "Ana",
            tipo: "Actividad",
            finReal: "2026-10-20",
            esfuerzo: 6,
          },
          { uid: "milestone", responsable: "Ana", tipo: "Hito", esfuerzo: 6 },
          {
            uid: "stopped",
            responsable: "Beto",
            estado: "Detenido",
            esfuerzo: 3,
          },
          {
            uid: "review",
            responsable: "Beto",
            estado: "Por validar",
            esfuerzo: 3,
          },
          { uid: "unknown", responsable: "Pendiente", esfuerzo: 2 },
          { uid: "zero", responsable: "Beto", esfuerzo: 0 },
          { uid: "undated", responsable: " Beto ", esfuerzo: "3" },
        ],
      ],
    ]) {
      test(`Capacity and resources match original without mutation (${name})`, () => {
        const dashboard = { ...data, plan: { filas: structuredClone(rows) } };
        scope.aerDashboardData = dashboard;
        const entry = {
          name,
          dashboard,
          expected: {
            resources: plain(scope._aerRecursosProyecto()),
            occupancy: plain(scope._aerOcupacionActualPorResponsable(rows)),
          },
          consumes: [null, ...rows].map((row) => ({
            row,
            expected: scope._aerFilaConsumeCapacidad(row, date),
          })),
          capacities: [],
        };
        group.capacity.push(entry);
        for (const args of [
          [
            "Ana",
            "2026-10-01",
            "2026-10-31",
            "",
            6,
            "En progreso",
            "Actividad",
          ],
          [
            "Ana",
            "2026-11-01",
            "2026-11-10",
            "future",
            3,
            "Por iniciar",
            "Actividad",
          ],
          ["Beto", "", "", "", 2, "Completado", "Actividad"],
          ["Ana", "2026-09-01", "2026-10-01", "past", 1, "En progreso", "Hito"],
          ["Pendiente", "", ""],
          ["", "", ""],
          ["Beto", "", "", "undated", 4, "En progreso", "Actividad"],
        ])
          entry.capacities.push({
            args,
            expected: plain(scope._aerMaxCapacidadEnRango(...args)),
          });
      });
    }

    for (const [name, text] of [
      ["empty", ""],
      ["invalid", "una columna"],
      [
        "tab",
        "Tipo\tActividad\tResponsable\tInicio_Plan\tFin_Plan\nActividad\tRevisión\tAna\t1/10\t23/10",
      ],
      ["semicolon", "Actividad;Entrega;Ana;01-10-2026;23-10-2026;;;100"],
      ["comma", "Actividad,Entrega,Ana,2026-10-01,2026-10-23,,,0"],
      ["spaces", "Actividad  Entrega  Ana  1/10  23/10"],
      [
        "omitted rows",
        "Tipo\tActividad\tResponsable\nActividad\t\tAna\nHito\tEntrega\tBeto",
      ],
      [
        "line endings",
        "Tipo\tActividad\r\nActividad\t\u00a0Entrega\rHito\tCierre",
      ],
    ]) {
      test(`Import parser preserves original limitations (${name})`, () => {
        scope.aerDashboardData = data;
        group.parsers.push({
          name,
          text,
          project: data.proyecto,
          expected: plain(scope._aerParsePlanText(text)),
        });
      });
    }
    test("Imported dates use project year and retain unrecognized input", () => {
      for (const project of [
        {},
        { fechaInicio: "2025-01-01" },
        { fechaFin: "2027-01-01" },
      ]) {
        scope.aerDashboardData = { proyecto: project };
        for (const value of [
          null,
          "",
          "2026-10-23",
          "1/10",
          "01-10-2026",
          "invalid",
        ])
          group.dates.push({
            project,
            value,
            expected: pack(scope._aerNormalizarFechaImport(value)),
          });
      }
    });

    // Execute the original calculation prefix; HTML is not used as the reference model.
    for (const name of [
      "_aerMonthValue",
      "_aerInitPlanFiltroMes",
      "_aerNormFilter",
      "_aerEsc",
    ]) {
      const match = source.match(
        new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`),
      );
      if (name === "_aerMonthValue")
        vm.runInNewContext(
          source.match(/  function _aerMonthValue[^\n]+/)[0],
          scope,
        );
      else vm.runInNewContext(match[0], scope);
    }
    const start = source.indexOf("  function _aerVistaPlaneacion()");
    vm.runInNewContext(
      source.slice(start, source.indexOf("    const kpi=", start)) +
        "return {pl,filas,fromMonth,toMonth,min,max,spanDays,pos,width,fmtShort,hoyIso,grouped,monthMap,weeks,todayPos,estadoCompromiso,total,cerrados,atiempo,vencidos,vencenHoy,proximos,vacaciones,vacacionesProximas,habiles30,vacDiasPorRecurso,vacWeeks,proximos7,hitosValidar,vencidosRows,detenidosRows,depStatus,esfuerzoPlan,esfuerzoCerrado,esfuerzoPendiente,avancePct,ocupacionActual,respRows,recursosConCap,puntosOcupados,capacidadTotal,puntosDisponibles,recursosOcupados,recursosSobrecargados,depUnique,depVencidas,depAbiertas,depDetenidas,bloqueosCriticos,attnCount};\n}",
      scope,
    );
    const enriched = structuredClone(data);
    enriched.plan.filas.push(
      ...[
        {
          uid: "today",
          tipo: "Actividad",
          actividad: "Hoy",
          responsable: "Ana",
          inicioPlan: "2026-10-01",
          finPlan: "2026-10-23",
          estado: "En progreso",
          esfuerzo: 6,
          dependencia: " Accesos ",
          estadoDependencia: "Resuelta",
        },
        {
          uid: "soon",
          tipo: "Hito",
          actividad: "Validación",
          responsable: "Ana",
          finPlan: "2026-10-25",
          estado: "Por validar",
          dependencia: "ACCESOS",
          estadoDependencia: "Detenida",
        },
        {
          uid: "next",
          tipo: "Actividad",
          actividad: "Próxima",
          responsable: "Beto",
          finPlan: "2026-10-27",
          estado: "En progreso",
          esfuerzo: 2,
        },
      ],
    );
    enriched.vacaciones = {
      filas: [
        {
          recurso: "Ana",
          inicio: "2026-10-20",
          fin: "2026-10-30",
          estado: "Aprobada",
        },
        {
          recurso: "Ana",
          inicio: "2026-10-26",
          fin: "2026-11-30",
          estado: "Pendiente",
        },
        {
          recurso: "Beto",
          inicio: "2026-10-23",
          fin: "2026-10-25",
          estado: "Cancelada",
        },
      ],
    };
    for (const [name, dashboard] of [
      ["empty", {}],
      ["original", data],
      ["attention", enriched],
    ]) {
      for (const range of [
        {},
        { desde: "2026-10", hasta: "2026-09" },
        { desde: "2026-08", hasta: "2026-12" },
      ]) {
        test(`Planning summary and timeline match original (${name}, ${JSON.stringify(range)})`, () => {
          scope.aerDashboardData = dashboard;
          scope.aerPlanFiltroMes = { ...range };
          const expected = scope._aerVistaPlaneacion();
          const functions = expected.filas.map((row) => ({
            row,
            state: pack(expected.estadoCompromiso(row)),
            dependency: pack(expected.depStatus(row)),
            width: pack(expected.width(row.inicioPlan, row.finPlan)),
            dates: [row.inicioPlan, row.finPlan, row.finReal].map((value) => ({
              input: pack(value),
              pos: pack(expected.pos(value)),
              short: pack(expected.fmtShort(value)),
            })),
          }));
          group.models.push({
            name,
            dashboard,
            range,
            expected: plain(expected),
            functions,
          });
        });
      }
    }
  }
} finally {
  if (previousTZ === undefined) delete process.env.TZ;
  else process.env.TZ = previousTZ;
}
captured.now = "2026-10-23T18:00:00Z";
captured.date = date;
fs.writeFileSync(
  "tests/frontend/frozen/aer_planning.json",
  JSON.stringify(captured, null, 2) + "\n",
);
