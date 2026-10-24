import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  isSummaryQuestion,
  summaryPayload,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_ai_actions_model.js";
const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const start = source.indexOf("  function aerIAPreguntar()");
const logic = source.slice(
  source.indexOf("    const normalized=question", start),
  source.indexOf(
    "    if(btn)",
    source.indexOf("    const normalized=question", start),
  ),
);
const original = vm.runInNewContext(
  "question=>{" + logic + "return isSummary;}",
  {},
);
for (const question of [
  "Resume el proyecto para comité",
  " RESUMEN EJECUTIVO ",
  "Resumen del estado",
  "¿Cuál es el riesgo?",
  "Puedes resume el proyecto para COMITÉ hoy",
  "resumen ejecutivo del cliente",
])
  test(`Question routing retains original decision: ${question}`, () =>
    assert.equal(isSummaryQuestion(question), original(question)));
test("Summary context preserves five selected files and exact instructions", () => {
  const statement = source.match(
    /    const payload=\{ids:\(aerIAState.seleccion[^\n]+/,
  )[0];
  for (const seleccion of [[], ["a"], ["1", "2", "3", "4", "5", "6"]]) {
    const state = { seleccion },
      scope = { aerIAState: state };
    vm.runInNewContext(statement + ";result=payload;", scope);
    const before = JSON.stringify(state);
    assert.deepEqual(
      summaryPayload(state, scope.result.instrucciones),
      JSON.parse(JSON.stringify(scope.result)),
    );
    assert.equal(JSON.stringify(state), before);
  }
});
