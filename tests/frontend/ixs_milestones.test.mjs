import test from "node:test";
import assert from "node:assert/strict";
import { collectRows, dmyToIso } from "../../frontend/static/scripts/pages/project_detail/sections/milestones_model.js";

const row = (extra) => ({ tipo: "🎥 Demo", nuevoNombre: "", icono: "🏁", fecha: "2026-11-01", obs: "", ...extra });

test("converts dd/mm/yyyy dates to ISO", () => {
  assert.equal(dmyToIso("5/1/2026"), "2026-01-05");
  assert.equal(dmyToIso("mal"), "");
});
test("new types get the chosen icon and edits keep their entry", () => {
  const out = collectRows([
    row({ tipo: "__nuevo__", nuevoNombre: " Cierre ", obs: "x" }),
    row({ editTipo: "🎥 Demo", editIndice: "2" }),
  ]);
  assert.deepEqual(out.nuevos, [{ tipo: "🏁 Cierre", fechaISO: "2026-11-01", observacion: "x" }]);
  assert.deepEqual(out.ediciones, [{ tipo: "🎥 Demo", indice: 2, fechaISO: "2026-11-01", observacion: "" }]);
});
test("keeps the original validation messages", () => {
  assert.equal(collectRows([row({ tipo: "__nuevo__", nuevoNombre: " " })]).error, "Falta el nombre de un tipo de hito nuevo.");
  assert.equal(collectRows([row({ fecha: "" })]).error, "Falta la fecha en uno de los hitos.");
  assert.equal(collectRows([]).error, "Agrega al menos un hito.");
});
