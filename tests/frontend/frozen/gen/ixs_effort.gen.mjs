// Temporary original-only capture; run from repository root.
const captured = { totals: [], rows: [], weeks: [] };
const test = (_name, callback) => callback();
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
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
  "_ixsCalcEffort",
  "_ixsActividadRows",
  "_ixsTrendRows",
  "_ixsExcessByPerson",
  "_ixsRecursoClave",
  "_ixsYmdLocal",
  "_ixsSemanaActual",
];
const context = { Date };
vm.runInNewContext(helperNames.map(original).join("\n"), context);
const json = (value) => JSON.parse(JSON.stringify(value));

test("effort keeps original totals, zero fallbacks, nonbillable hours and rounding", () => {
  const samples = JSON.parse(
    fs.readFileSync("tests/ejecutivo/project_integrated_expected.json", "utf8"),
  ).slice(5, 12);
  const variants = [{}, ...samples];
  for (const value of [0, null, -2.1234, 17.99999]) {
    const d = structuredClone(samples[0]);
    d.totalesRecursos = {
      horasReales: value,
      horasNoFact: value,
      horasEstimadas: value,
      costoReal: value,
      pctCumplimientoFinanciero: value,
    };
    d.kpisExtra.horasFueraHorario = 2.5;
    variants.push(d);
  }
  for (const data of variants) {
    captured.totals.push({
      data,
      expected: json(context._ixsCalcEffort(data)),
    });
  }
});

test("activities, trend and billable excess preserve grouping, chronology and deduplication", () => {
  const resources = [
    { nombre: "Ana Pérez", posicion: "Developer", horasEstimadas: 10 },
    { nombre: "Sin horas", horasEstimadas: 0 },
  ];
  const records = [
    {
      id: "2",
      recurso: "ANA PEREZ",
      fecha: "2026-10-03",
      inicio: "10:00",
      duracion: 8,
      billable: true,
      actividad: "Dev",
    },
    {
      id: "1",
      recurso: "Ana Pérez",
      fecha: "2026-10-01",
      inicio: "09:00",
      duracion: 8,
      billable: true,
      actividad: "Dev",
    },
    {
      id: "2",
      recurso: "ANA PEREZ",
      fecha: "2026-10-03",
      inicio: "10:00",
      duracion: 8,
      billable: true,
      actividad: "Dev",
    },
    { recurso: "Externo", fecha: "2026-09-01", duracion: 1.5, billable: true },
    {
      recurso: "Ana Pérez",
      fecha: "2026-08-01",
      duracion: 4,
      billable: false,
      actividad: "INV_OPERATIVA",
    },
    { recurso: "Ana Pérez", fecha: "invalid", duracion: -1, billable: true },
    { recurso: "Ana Pérez", fecha: "2026-07-01", duracion: 0, billable: true },
    {
      recurso: "Ana Pérez",
      fecha: "2026-06-01",
      duracion: 4,
      billable: "true",
    },
    {
      recurso: " ",
      fecha: "2026-05-01",
      duracion: 3,
      billable: true,
      actividad: " ",
    },
  ];
  for (const rows of [[], records, [...records].reverse()]) {
    captured.rows.push({
      resources,
      input: rows,
      expected: json({
        activities: context._ixsActividadRows(rows),
        trend: context._ixsTrendRows(rows),
        excess: context._ixsExcessByPerson(resources, rows),
      }),
    });
  }
});

test("default week preserves local Monday through Sunday across year boundaries", () => {
  const NativeDate = Date;
  try {
    for (const date of [
      "2026-10-23T18:00:00Z",
      "2026-10-25T18:00:00Z",
      "2026-10-26T18:00:00Z",
      "2027-01-01T18:00:00Z",
    ]) {
      class FixedDate extends NativeDate {
        constructor(...args) {
          super(...(args.length ? args : [date]));
        }
      }
      globalThis.Date = FixedDate;
      context.Date = FixedDate;
      captured.weeks.push({ date, expected: json(context._ixsSemanaActual()) });
    }
  } finally {
    globalThis.Date = NativeDate;
    context.Date = NativeDate;
  }
});

fs.writeFileSync(
  "tests/frontend/frozen/ixs_effort.json",
  JSON.stringify(captured, null, 2) + "\n",
);
