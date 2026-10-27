import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  stage,
  aerStatus,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_shell_model.js";
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
  test(`Header stage matches original: ${label}`, () => {
    const before = JSON.stringify(data);
    assert.deepEqual(
      stage(data, new Date(now)),
      JSON.parse(JSON.stringify(scope._ixsEtapaActual(data))),
    );
    assert.equal(JSON.stringify(data), before);
  });
test("AER badge preserves original classification and defaults", () => {
  for (const value of [
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
  ])
    assert.equal(aerStatus(value), scope._aerEstadoClase(value));
});
