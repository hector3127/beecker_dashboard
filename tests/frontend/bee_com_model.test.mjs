import test from "node:test";
import assert from "node:assert/strict";
import { countsByType, inScope, keyPoints, payloadOf, projectsOf, rowSummary, visible } from "../../frontend/static/scripts/pages/project_detail/sections/bee_com_model.js";

const items = [
  { uid: "1", fecha: "2026-10-20", titulo: "Uno", categoria: "Aviso", proyecto: "A", resumen: "", contenido: "x".repeat(200), autor: "Ana" },
  { uid: "2", fecha: "2026-10-22", titulo: "Dos", categoria: "Cambio", proyecto: "", resumen: "Resumen", contenido: "y", autor: "" },
  { uid: "3", fecha: "2026-10-21", titulo: "Tres", categoria: "Aviso", proyecto: "B", resumen: "", contenido: "z", autor: "Luis" },
];

test("a project sees its own communications and the general ones", () => {
  assert.deepEqual(inScope(items, "A").map((x) => x.uid), ["1", "2"]);
  assert.equal(inScope(items, "").length, 3);
  assert.deepEqual(projectsOf(items), ["A", "B"]);
  assert.equal(countsByType(items).Aviso, 2);
});

test("filters combine, search ignores case and order follows the date", () => {
  const base = { tipo: "Todos", proyecto: "", busqueda: "", orden: "recientes" };
  assert.deepEqual(visible(items, base).map((x) => x.uid), ["2", "3", "1"]);
  assert.deepEqual(visible(items, { ...base, orden: "antiguos" }).map((x) => x.uid), ["1", "3", "2"]);
  assert.deepEqual(visible(items, { ...base, tipo: "Aviso", busqueda: "LUIS" }).map((x) => x.uid), ["3"]);
  assert.deepEqual(visible(items, { ...base, proyecto: "B" }).map((x) => x.uid), ["3"]);
});

test("key points drop bullets and numbering; rows fall back to the content", () => {
  assert.deepEqual(keyPoints("• Uno\n2. Dos\n- Tres\n\n  * Cuatro "), ["Uno", "Dos", "Tres", "Cuatro"]);
  assert.deepEqual(keyPoints(null), []);
  assert.equal(rowSummary(items[0]).length, 140);
  assert.equal(rowSummary(items[1]), "Resumen");
});

test("the saved payload carries the uid, the form fields and the checkbox", () => {
  const form = new FormData();
  form.append("titulo", "T");
  form.append("categoria", "Aviso");
  assert.deepEqual(payloadOf(form, "u1", true), { uid: "u1", titulo: "T", categoria: "Aviso", importante: true });
});
