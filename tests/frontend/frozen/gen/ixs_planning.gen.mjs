// Temporary original-only capture. Run explicitly from repository root.

import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
function original(name) {
  const line = source
    .split("\n")
    .find((x) => x.startsWith(`  function ${name}(`));
  return line.trim().endsWith("}")
    ? line
    : source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0];
}
const NativeDate = Date;
class FixedDate extends NativeDate {
  constructor(...args) {
    super(...(args.length ? args : ["2026-10-23T18:00:00Z"]));
  }
  static now() {
    return +new NativeDate("2026-10-23T18:00:00Z");
  }
}
const context = { Date: FixedDate };
vm.runInNewContext(
  [
    "_ixsDateMs",
    "_ixsFases",
    "_ixsHitos",
    "_ixsRecursoClave",
    "nombreLimpioHito",
    "categoriaHito",
  ]
    .map(original)
    .join("\n"),
  Object.assign(context, { EMOJI_REGEX: /\p{Extended_Pictographic}/u }),
);
const calculation = original("_ixsPintarPlaneacion")
  .split("    const resumen=")[1]
  .split("    box.innerHTML=")[0];
vm.runInNewContext(
  original("_ixsAz84Status") +
    original("_ixsAz84Stage") +
    original("_ixsPlanResumen") +
    "\nfunction projection(d,st){const resumen=" +
    calculation +
    "return {summary:resumen,hitos,completed:completados,underway:enCurso,items,closed,dated:conFecha,resources:recursos,weeks:vacWeeks,byStage:[...byStage].sort((a,b)=>b[1]-a[1]).slice(0,4)};}",
  context,
);
const plain = (value) => JSON.parse(JSON.stringify(value));
const plans = [
  { vacaciones: [], compromisos: [] },
  {
    vacaciones: [
      {
        recurso: "Ana Pérez",
        inicio: "2026-10-23",
        fin: "2026-10-30",
        estado: "Aprobada",
      },
      {
        recurso: "ANA PEREZ",
        inicio: "2026-10-26",
        fin: "2026-11-03",
        estado: "Pendiente",
      },
      {
        recurso: "Luis",
        inicio: "2026-10-24",
        fin: "2026-10-27",
        estado: "Cancelada",
      },
      { recurso: "Lea", inicio: "2026-11-22", fin: "2026-11-28" },
      { recurso: "Sin fecha", inicio: "invalid", fin: "2026-10-30" },
    ],
    compromisos: [
      {
        tipo: "Hito",
        actividad: "Entrega",
        fecha: "2026-11-02",
        estado: "Pendiente",
      },
    ],
  },
];
const azure = {
  items: [
    {
      id: 1,
      estado: " Active ",
      fechaLimiteDev: "2026-10-22",
      iterationPath: "AMK\\Development",
    },
    {
      id: 2,
      estado: "Blocked",
      fechaLimiteDev: "2026-10-23",
      iterationPath: "AMK\\Development",
    },
    {
      id: 3,
      estado: "Proposed",
      fechaLimiteDev: "2026-10-30",
      iterationPath: "AMK\\Deployment",
    },
    { id: 4, estado: "Closed", fechaLimiteDev: "2026-10-22" },
    { id: 5, estado: "Cancelled", fechaLimiteDev: "2026-10-22" },
    { id: 6, estado: "Other", fechaLimiteDev: "invalid" },
  ],
};

const captured = {};
const previousTZ = process.env.TZ;
try {
  for (const zone of ["UTC", "America/Mexico_City"]) {
    process.env.TZ = zone;
    const groups = (captured[zone] = { summary: [], model: [] });
    const test = (_name, callback) => callback();
    test("planning deadlines and vacations preserve the original date boundaries and states", () => {
      globalThis.Date = FixedDate;
      try {
        for (const plan of plans)
          for (const az of [{ items: [] }, azure]) {
            context.ixsPlanState = plan;
            context.ixsPlanAzureState = az;
            groups.summary.push({
              plan,
              azure: az,
              expected: plain(context._ixsPlanResumen()),
            });
          }
      } finally {
        globalThis.Date = NativeDate;
      }
    });

    test("planning indicators, stage ranking and six-week distinct resources match the old renderer", () => {
      globalThis.Date = FixedDate;
      try {
        const fixture = JSON.parse(
          fs.readFileSync(
            "tests/ejecutivo/project_integrated_expected.json",
            "utf8",
          ),
        )[5];
        for (const data of [{ proyecto: { id: "Empty" } }, fixture])
          for (const plan of plans) {
            context.ixsPlanState = plan;
            context.ixsPlanAzureState = azure;
            groups.model.push({
              data,
              plan,
              azure,
              expected: plain(context.projection(data, plan)),
            });
          }
      } finally {
        globalThis.Date = NativeDate;
      }
    });
    // Additional regression: middle/end of week must not collapse to tomorrow.
    const boundaryAzure = {
      items: [
        "2026-10-22",
        "2026-10-23",
        "2026-10-24",
        "2026-10-26",
        "2026-10-29",
        "2026-10-30",
        "2026-10-31",
      ].map((fechaLimiteDev, i) => ({
        id: 20 + i,
        estado: "Active",
        fechaLimiteDev,
      })),
    };
    context.ixsPlanState = plans[0];
    context.ixsPlanAzureState = boundaryAzure;
    groups.summary.push({
      plan: plans[0],
      azure: boundaryAzure,
      expected: plain(context._ixsPlanResumen()),
    });
  }
} finally {
  if (previousTZ === undefined) delete process.env.TZ;
  else process.env.TZ = previousTZ;
}
captured.now = "2026-10-23T18:00:00Z";
fs.writeFileSync(
  "tests/frontend/frozen/ixs_planning.json",
  JSON.stringify(captured, null, 2) + "\n",
);
