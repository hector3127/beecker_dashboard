import fs from "node:fs";
import vm from "node:vm";
// Temporary explicit capture from the original, not current models.
const captured = [];
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const now = "2026-10-23T18:00:00Z";
const scope = {
  Date: class extends Date {
    constructor(...args) {
      super(...(args.length ? args : [now]));
    }
  },
};
for (const name of [
  "_aerEsc",
  "_ixsDateMs",
  "_ixsFases",
  "_ixsEtapaActual",
  "_aerEstadoClase",
])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    scope,
  );
scope._ixsTxt = scope._aerEsc;
for (const [label, data] of [
  ["empty", {}],
  ["closed", { cerrado: true }],
  [
    "suspended",
    { suspensiones: [{ fechaInicio: "2026-10-20", fechaFin: "2026-10-25" }] },
  ],
  [
    "active",
    {
      historialCompleto: [
        {
          fase: "R&D <fase>",
          fechaInicio: "2026-10-01",
          fechaFin: "2026-11-01",
          enCurso: true,
        },
      ],
    },
  ],
  [
    "first day",
    {
      historialCompleto: [
        { fase: "Inicio", fechaInicio: "2026-10-23", fechaFin: "2026-10-24" },
      ],
    },
  ],
  [
    "future",
    {
      hitos: [
        { nombre: "Futuro", fechaInicioPlan: "2026-10-30" },
        { nombre: "Más cercano", fechaInicioPlan: "2026-10-24" },
      ],
    },
  ],
  [
    "last",
    {
      historialCompleto: [
        { fase: "Primera", fechaInicio: "2026-08-01", fechaFin: "2026-08-10" },
        { fase: "Última", fechaInicio: "2026-09-01", fechaFin: "2026-09-10" },
      ],
    },
  ],
  [
    "invalid dates",
    {
      suspensiones: [{ fechaInicio: "bad" }],
      hitos: [{ nombre: "bad", fechaInicioPlan: "bad" }],
    },
  ],
])
  captured.push({
    label,
    data: JSON.parse(JSON.stringify(data)),
    expected: JSON.parse(JSON.stringify(scope._ixsEtapaActual(data))),
  });
const statuses = [
  null,
  "",
  "Crítico",
  "Atrasado",
  "En tiempo",
  "Cerrado",
  "Pendiente",
  "Pausado",
  "En progreso",
  "Por validar",
  "Otro",
].map((input) => ({ input, expected: scope._aerEstadoClase(input) }));
fs.writeFileSync(
  "tests/frontend/frozen/project_shell.json",
  JSON.stringify({ stages: captured, statuses }, null, 2) + "\n",
);
console.log(
  "Captured",
  captured.length,
  "stages and",
  statuses.length,
  "AER statuses.",
);
