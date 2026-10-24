import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { actionsModel } from "../../frontend/static/scripts/pages/project_detail/sections/actions_model.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const original = source.slice(
  source.indexOf("  function _aerVistaAcciones()"),
  source.indexOf(
    '    return `<div class="aer-action-shell">',
    source.indexOf("  function _aerVistaAcciones()"),
  ),
);
const fields =
  "ac,filas,hoyIso,abiertas,vencidas,detenidas,proximas,urgente,respCount,respTop,weeks";
const scope = {
  window: {},
  Date: class extends Date {
    constructor(...args) {
      super(...(args.length ? args : ["2026-10-23T12:00:00Z"]));
    }
  },
};
vm.runInNewContext(
  source.match(/  function _aerAccionFechaPrincipal\([\s\S]*?\n  \}/)[0] +
    "\n" +
    original +
    `return {${fields}};\n}`,
  scope,
);
const plain = (x) => JSON.parse(JSON.stringify(x));

for (const [name, dashboard] of [
  ["empty", {}],
  [
    "full",
    {
      acciones: {
        filas: [
          {
            uid: "1",
            responsable: " Ana ",
            estado: "Completado",
            fechaLimite: "2026-10-23",
          },
          {
            uid: "2",
            responsable: "Luis",
            estado: "Detenido",
            fechaInicio: "2026-11-03",
          },
          { uid: "3", responsable: "", proximaRevision: "2026-10-30" },
          { uid: "4", responsable: "Luis", fechaReal: "2026-10-24" },
          { uid: "5", responsable: "Ana", fechaLimite: "invalid" },
        ],
        abiertas: [1, 2],
        vencidas: [{ uid: "3", accion: "Prioritaria" }],
        detenidas: [1],
      },
    },
  ],
  [
    "no dates",
    {
      acciones: {
        filas: [
          { responsable: "Ana" },
          { responsable: "Luis", estado: "Detenido" },
        ],
      },
    },
  ],
]) {
  test(`Actions summary matches legacy (${name}) without mutating input`, () => {
    const before = JSON.stringify(dashboard);
    scope.aerDashboardData = dashboard;
    assert.deepEqual(
      plain(actionsModel(dashboard, "2026-10-23")),
      plain(scope._aerVistaAcciones()),
    );
    assert.equal(JSON.stringify(dashboard), before);
  });
}
