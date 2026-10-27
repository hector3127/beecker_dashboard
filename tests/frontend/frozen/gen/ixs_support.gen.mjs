// Temporary original-only capture; run from repository root.
const captured = [];
const test = (_name, callback) => callback();
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const NativeDate = Date;
const FixedDate = class extends NativeDate {
  constructor(...args) {
    super(...(args.length ? args : ["2026-10-23T18:00:00Z"]));
  }
};
const original = {
  Date: FixedDate,
  window: {},
  IXE_STAGES: ["Discovery", "Development", "Deployment"],
};
for (const name of ["_ixsDateMs", "_ixsFases", "_ixeAuto"])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
    original,
  );
for (const name of ["_ixeIso", "_ixeStageOf"])
  vm.runInNewContext(
    source.match(new RegExp(`  function ${name}[^\\n]+`))[0],
    original,
  );

for (const [label, data] of [
  ["empty", {}],
  [
    "planned",
    { hitos: [{ nombre: "Discovery EST", fechaFinPlan: "2010-03-20" }] },
  ],
  [
    "closed",
    {
      historialCompleto: [
        {
          fase: "Development",
          fechaInicio: "2010-01-01",
          fechaFin: "2010-03-02",
        },
      ],
      hitos: [{ nombre: "Development EST", fechaFinPlan: "2010-04-01" }],
    },
  ],
  [
    "active prefers planned close",
    {
      historialCompleto: [
        {
          fase: "Deployment",
          fechaInicio: "2010-01-01",
          fechaFin: "2010-03-02",
          enCurso: true,
        },
      ],
      hitos: [{ nombre: "Deployment EST", fechaFinPlan: "2010-04-01" }],
    },
  ],
  [
    "multiple cuts",
    {
      historialCompleto: [
        {
          fase: "Development",
          fechaInicio: "2010-01-01",
          fechaFin: "2010-02-02",
        },
        {
          fase: "Development",
          fechaInicio: "2010-02-01",
          fechaFin: "2010-03-01",
        },
        { fase: "Other", fechaInicio: "2010-04-01", fechaFin: "2010-05-01" },
      ],
    },
  ],
  [
    "Latin dates",
    {
      historialCompleto: [
        {
          fase: "DISCOVERY",
          fechaInicio: "01/02/2010",
          fechaFin: "28/02/2010",
        },
      ],
    },
  ],
]) {
  test(`suggested stage and close dates match previous: ${label}`, () => {
    captured.push({
      label,
      data,
      expected: JSON.parse(JSON.stringify(original._ixeAuto(data))),
    });
  });
}

fs.writeFileSync(
  "tests/frontend/frozen/ixs_support.json",
  JSON.stringify(captured, null, 2) + "\n",
);
