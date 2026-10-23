// @ts-check
// Reglas del alta RAID: textos por tipo, sugerencias, estado del padre y la
// preparación de los datos que se publican en Azure DevOps.
import { severityNumber } from "./raid_model.js";

export const SUGGEST_KEYS = ["responsable", "iterationPath", "reporter", "escalationContact", "personaEscala", "relatedWorkItemId"];

/** @type {Record<string, {intro: string, noun: string}>} */
export const COPY = {
  Risk: { intro: "Describe una amenaza potencial; Claude reutiliza tu generador actual de riesgos.", noun: "riesgo" },
  Issue: { intro: "Describe un problema que ya está ocurriendo.", noun: "issue" },
  Opportunity: { intro: "Describe una posibilidad favorable para mejorar el proyecto.", noun: "beneficio potencial" },
};

/** Una acción del plan por línea, aun si Claude junta todas las viñetas. @param {any} text */
export function planLines(text) {
  const raw = String(text || "").replace(/\r/g, "");
  const lines = raw
    .replace(/\s*[•●▪]\s*/g, "\n• ")
    .replace(/(?:^|\n)\s*(?:\*|-|\d+[.)])\s+/g, "\n• ")
    .split(/\n+/)
    .map((s) => s.trim().replace(/^•\s*/, "").trim())
    .filter(Boolean);
  return lines.map((s) => "• " + s).join("\n");
}

/** Opciones del buscador de cada campo. @param {string} key @param {any} cfg */
export function suggestions(key, cfg) {
  const c = cfg || {};
  if (["responsable", "reporter", "escalationContact", "personaEscala"].includes(key)) {
    return (c.usuarios || []).map((/** @type {any} */ u) => ({ text: u.nombre + (u.email ? " · " + u.email : ""), value: u.valor || u.email || u.nombre, keywords: (u.nombre + " " + u.email).toLowerCase() }));
  }
  if (key === "iterationPath") return (c.iteraciones || []).map((/** @type {string} */ path) => ({ text: path, value: path, keywords: path.toLowerCase() }));
  if (key === "relatedWorkItemId") return (c.relacionados || []).map((/** @type {any} */ w) => ({ text: "#" + w.id + " · " + w.titulo + " (" + w.tipo + ")", value: String(w.id), keywords: (w.id + " " + w.titulo + " " + w.tipo).toLowerCase() }));
  return [];
}

/** Texto y color de la línea de estado del Work Item padre. @param {string} raw @param {any} cfg */
export function parentStatus(raw, cfg) {
  const value = raw.trim().replace(/^#/, "");
  if (!value) return { text: "Sin padre seleccionado. Si eliges uno, este nuevo registro quedará como Child.", color: "#766d96" };
  if (!/^\d+$/.test(value)) return { text: "Selecciona un Work Item sugerido o escribe un ID numérico.", color: "#c92e50" };
  const known = ((cfg && cfg.relacionados) || []).find((/** @type {any} */ x) => String(x.id) === value);
  return { text: (known ? "✓ Padre seleccionado #" : "Padre indicado #") + value + (known ? " · " + known.titulo : " · se verificará en Azure al guardar") + "; el nuevo WI será su Child al crearlo.", color: known ? "#178354" : "#5b38cf" };
}

/**
 * Valida y prepara lo que se publica; devuelve el primer error con el mismo
 * texto de la pantalla anterior.
 * @param {string} tipo @param {Record<string, string>} data @param {any} cfg
 * @returns {{error: string} | {data: Record<string, string>}}
 */
export function prepareCreate(tipo, data, cfg) {
  const out = { ...data };
  if (tipo === "Issue") {
    delete out.primerSeguimiento;
    out.planMitigacion = planLines(out.planMitigacion);
  }
  const n = severityNumber(out.severidad);
  out.impactoNivel = n;
  if (tipo === "Issue") out.probabilidad = n;
  if (!out.titulo || !out.descripcion) return { error: "Completa título y descripción antes de crear." };
  const c = cfg || {};
  if (!c.iteraciones || !c.iteraciones.length) return { error: "Todavía no hay iteraciones verificadas del proyecto Azure. Espera a que terminen de cargarse las sugerencias." };
  const normalize = (/** @type {any} */ p) => String(p || "").trim().toLowerCase();
  const valid = c.iteraciones.find((/** @type {string} */ p) => normalize(p) === normalize(out.iterationPath || c.iteracionDefault));
  if (!valid) return { error: "Iteration Path no válido: selecciona una ruta de la lista real de Azure para " + c.proyectoAzure + "." };
  out.iterationPath = valid;
  if (out.relatedWorkItemId && !/^#?\d+$/.test(out.relatedWorkItemId)) return { error: "Selecciona un Work Item sugerido o escribe su ID numérico." };
  return { data: out };
}

/** Aviso tras crear. @param {any} r */
export function createdNotice(r) {
  if (r.parentId) {
    return r.vinculoConfirmado ? `✓ WI #${r.childId} creado como CHILD de #${r.parentId} (PARENT) en Azure.` : `⚠ WI #${r.childId} creado. ${r.aviso || "No se pudo confirmar el vínculo Parent → Child; revísalo en Azure."}`;
  }
  return `✓ Registro #${r.id} creado correctamente.`;
}
