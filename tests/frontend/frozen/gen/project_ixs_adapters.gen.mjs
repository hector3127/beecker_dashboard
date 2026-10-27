// Temporary original-only capture.
const captured = [];
const test = (_name, callback) => callback();
import fs from "node:fs";
import vm from "node:vm";
import { originalState } from "./project_original_state.mjs";
const scopes = new WeakMap();
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const plain = (value) => JSON.parse(JSON.stringify(value));
function original(store) {
  const scope = scopes.get(store);
  vm.runInNewContext(source.match(/const EMOJI_REGEX[^\n]+/)[0], scope);
  for (const name of [
    "_ixsDateMs",
    "_ixsFases",
    "_ixsHitos",
    "nombreLimpioHito",
    "categoriaHito",
    "ixsIAContexto",
    "ixsIASnapshot",
    "ixsIACambios",
    "ixsIACapacidad",
  ])
    vm.runInNewContext(
      source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0],
      scope,
    );
  return scope;
}
for (const variant of ["empty", "milestones", "memory"])
  test(`${variant}: composed IA data matches original formulas and milestone preparation`, () => {
    const { store, scope } = originalState(source);
    scopes.set(store, scope);
    store.ixsAi.id = "P";
    if (variant !== "empty") {
      store.ixs = {
        proyecto: { id: "P", nombre: "Proyecto" },
        hitos: [
          {
            nombre: "Discovery",
            fechaInicioPlan: "2010-01-01",
            fechaFinPlan: "2010-02-01",
          },
        ],
        historialCompleto: [
          {
            fase: "Discovery",
            fechaInicio: "2010-01-02",
            fechaFin: "2010-02-05",
          },
        ],
        hitosAdicionales: [
          {
            tipo: "🎥 Demo <cliente>",
            fecha: "2010-01-20",
            indice: 7,
            observacion: "Notas",
          },
        ],
      };
      Object.assign(store.ixsAi, {
        azure: {
          allItems: [
            { id: 1, state: "Closed", assignedTo: { displayName: "Ana" } },
          ],
        },
        clockify: {
          registros: [{ recurso: "Ana", duracion: 2.5, fecha: "2010-01-01" }],
        },
        resources: {
          filas: [{ nombre: "Ana", horasEstimadas: 8, activo: true }],
        },
        plan: { compromisos: [], vacaciones: [] },
        cliente: { acciones: { filas: [] } },
      });
    }
    const old = original(store);
    if (variant === "memory") {
      const previous = plain(old.ixsIASnapshot());
      previous.workItems[0].estado = "Active";
      previous.horas = 1;
      store.ixsAi.memoria = { actual: { snapshot: previous } };
    }
    captured.push({
      variant,
      input: plain({ ixs: store.ixs, ixsAi: store.ixsAi }),
      expected: plain({
        context: old.ixsIAContexto(),
        snapshot: old.ixsIASnapshot(),
        changes: old.ixsIACambios(),
        capacity: old.ixsIACapacidad(),
      }),
    });
  });
fs.writeFileSync(
  "tests/frontend/frozen/project_ixs_adapters.json",
  JSON.stringify(captured, null, 2) + "\n",
);
