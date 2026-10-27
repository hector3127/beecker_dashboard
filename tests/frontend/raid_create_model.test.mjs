import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { createdNotice, parentStatus, planLines, prepareCreate, suggestions } from "../../frontend/static/scripts/pages/project_detail/sections/raid_create_model.js";

const original = fs.readFileSync("tests/reference/static/portal/js/proyecto_detalle.js", "utf8");
const legacyPlan = {};
vm.runInNewContext(original.match(/  function ixsRaidPlanEnLineas\([\s\S]*?\n  \}/)[0] + "\nthis.f=ixsRaidPlanEnLineas;", legacyPlan);

test("plan lines match the original function", () => {
  for (const text of ["", null, "• a • b ● c", "- uno\n* dos\n3) tres\n4. cuatro", "Una sola\r\nlinea", "1. x 2. y"]) assert.equal(planLines(text), legacyPlan.f(text));
});

const cfg = { iteraciones: ["AMK", "AMK\\Dev"], iteracionDefault: "AMK", proyectoAzure: "AMK", relacionados: [{ id: 5, titulo: "Épica", tipo: "Epic" }], usuarios: [{ nombre: "Ana", email: "a@x.com", valor: "Ana <a@x.com>" }] };

test("publishing rules and derived fields", () => {
  assert.equal(prepareCreate("Risk", { titulo: "", descripcion: "x" }, cfg).error, "Completa título y descripción antes de crear.");
  assert.match(prepareCreate("Risk", { titulo: "t", descripcion: "d" }, { iteraciones: [] }).error, /Todavía no hay iteraciones/);
  assert.match(prepareCreate("Risk", { titulo: "t", descripcion: "d", iterationPath: "Otra" }, cfg).error, /Iteration Path no válido.*AMK\./);
  assert.match(prepareCreate("Risk", { titulo: "t", descripcion: "d", relatedWorkItemId: "x" }, cfg).error, /ID numérico/);
  const issue = prepareCreate("Issue", { titulo: "t", descripcion: "d", severidad: "2 - Alto", iterationPath: "amk\\dev", planMitigacion: "- a\n- b", primerSeguimiento: "z" }, cfg).data;
  assert.deepEqual([issue.iterationPath, issue.impactoNivel, issue.probabilidad, issue.planMitigacion, "primerSeguimiento" in issue], ["AMK\\Dev", "2", "2", "• a\n• b", false]);
  assert.equal(prepareCreate("Risk", { titulo: "t", descripcion: "d", severidad: "3", probabilidad: "Alto" }, cfg).data.probabilidad, "Alto");
});

test("suggestions, parent status and creation notices", () => {
  assert.equal(suggestions("responsable", cfg)[0].value, "Ana <a@x.com>");
  assert.equal(suggestions("relatedWorkItemId", cfg)[0].text, "#5 · Épica (Epic)");
  assert.deepEqual(suggestions("otro", cfg), []);
  assert.match(parentStatus("#5", cfg).text, /✓ Padre seleccionado #5 · Épica/);
  assert.equal(parentStatus("zz", cfg).color, "#c92e50");
  assert.match(parentStatus("", cfg).text, /^Sin padre seleccionado\./);
  assert.equal(createdNotice({ id: 9 }), "✓ Registro #9 creado correctamente.");
  assert.match(createdNotice({ parentId: 1, childId: 2, vinculoConfirmado: true }), /CHILD de #1/);
  assert.match(createdNotice({ parentId: 1, childId: 2 }), /No se pudo confirmar el vínculo/);
});
