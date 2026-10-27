// Temporary original-only capture; run explicitly from repository root.
const captured = { models: [], editors: [] };
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
const json = (value) => JSON.parse(JSON.stringify(value));
const calculation = original("_ixsPintarRecursos")
  .split("    const base=")[1]
  .split("    box.innerHTML=")[0];
const context = {};
vm.runInNewContext(
  original("_ixsRecursoClave") +
    "\nfunction oracle(d,st){const base=" +
    calculation +
    "return {rows,hours,missing,inactive};}",
  context,
);
const plain = (model) => json({ ...model, hours: [...model.hours] });

test("resources preserve normalization, overrides, duplicate hours and alerts", () => {
  const base = JSON.parse(
    fs.readFileSync("tests/ejecutivo/project_integrated_expected.json", "utf8"),
  )[5];
  const inputs = [
    [{}, { filas: [], registros: [] }],
    [base, { filas: [], registros: [] }],
    [
      base,
      {
        filas: [
          {
            nombre: "  ANA PEREZ ",
            rol: "Lead",
            horasEstimadas: 0,
            activo: false,
          },
          {
            nombre: "O'Connor",
            rol: "QA",
            horasEstimadas: 12.25,
            activo: true,
          },
        ],
        registros: [
          { id: "same", recurso: "Ana Pérez", duracion: 8 },
          { id: "same", recurso: "ANA PEREZ", duracion: 8 },
          { recurso: "Sin asignación", duracion: 1.5 },
          { recurso: "O'Connor", duracion: -2 },
          { recurso: "", duracion: 8 },
          { recurso: "Otro", duracion: "invalid" },
        ],
      },
    ],
    [
      {
        filasRecursosCompleto: [
          { nombre: "A", posicion: "Base", horasEstimadas: 10 },
          { nombre: "a", posicion: "Duplicate", horasEstimadas: 99 },
        ],
      },
      {
        filas: [
          { nombre: "A", rol: "QA", activo: true },
          { nombre: "a", rol: "Last", activo: false },
        ],
        registros: [{ recurso: "A", duracion: 0 }],
      },
    ],
  ];
  for (const [data, state] of inputs) {
    captured.models.push({
      data,
      state,
      expected: plain(context.oracle(data, state)),
    });
  }
});

test("editor source keeps assignment-first fallback and exact names", () => {
  const setup =
    original("ixsAbrirEditorRecurso").split(
      "    const modal=document.createElement",
    )[0] + "return src;}";
  vm.runInNewContext(setup, context);
  const data = {
    filasRecursosCompleto: [
      { nombre: "Ana Pérez", posicion: "Developer", horasEstimadas: 10 },
      { nombre: "Fallback", posicion: "PM" },
    ],
  };
  const state = { filas: [{ nombre: "ANA PEREZ", rol: "QA", activo: false }] };
  context.ixsProyectoActual = data;
  context.ixsRecursosState = state;
  for (const name of ["Ana Pérez", "Fallback", "O'Connor", ""]) {
    captured.editors.push({
      data,
      state,
      name,
      expected: json(context.ixsAbrirEditorRecurso(encodeURIComponent(name))),
    });
  }
});

fs.writeFileSync(
  "tests/frontend/frozen/ixs_resources.json",
  JSON.stringify(captured, null, 2) + "\n",
);
