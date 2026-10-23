// @ts-check
// Reglas de Gestión RAID: severidad, cerrados, métricas y filtros. Son las
// mismas del renderer anterior, sin tocar el DOM.

export const TYPES = {
  Risk: { label: "Riesgo", icon: "⚠", color: "#e63b5e" },
  Issue: { label: "Issue", icon: "!", color: "#e99c1a" },
  Opportunity: { label: "Oportunidad", icon: "✦", color: "#0fa672" },
};
const CLOSED = ["NOT APPLICABLE", "CANCELLED", "CLOSED", "REJECTED", "COMPLETED", "INACTIVE"];

/** @param {any} row */
export const typeOf = (row) => /** @type {any} */ (TYPES)[row.tipo] || { label: row.tipo || "Registro", icon: "•", color: "#6742dc" };
/** @param {any} row */
export const isClosed = (row) => !!row.cerrado || CLOSED.includes(String(row.estado || "").toUpperCase());
/** @param {string} url */
export const safeLink = (url) => (/^https:\/\/dev\.azure\.com\//i.test(String(url || "")) ? String(url) : "#");
/** @param {string} path */
export const iteration = (path) => (path || "").split("\\").pop() || "";

/** @param {any} value */
export function severityNumber(value) {
  const m = String(value == null ? "" : value).trim().match(/^(\d+)(?=\s*[-–—]\s*|\s*$)/);
  return m ? String(Number(m[1])) : "";
}

/** @param {any} value */
export function level(value) {
  const n = String(value == null ? "" : value).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
  const num = severityNumber(n);
  if (num === "1") return "Alto";
  if (num === "2") return "Medio";
  if (num === "3" || num === "4") return "Bajo";
  if (/critical|critico|very high|muy alto|alto|\bhigh\b/.test(n)) return "Alto";
  if (/medio|medium|moderate/.test(n)) return "Medio";
  if (/bajo|low/.test(n)) return "Bajo";
  return "";
}

/** La severidad numérica también fija impacto (y probabilidad en Issues). @param {any} row */
export function normalizeSeverity(row) {
  const n = severityNumber(row && row.severidad);
  if (!n) return row;
  return { ...row, impacto: n, probabilidad: row.tipo === "Issue" ? n : row.probabilidad };
}

/** Texto de Azure sin etiquetas. @param {any} v */
export const cleanHtml = (v) =>
  String(v == null ? "" : v)
    .replace(/<br\s*\/?\s*>/gi, "\n")
    .replace(/<\/li\s*>/gi, "\n")
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .trim();

/** @param {any[]} rows */
export function summary(rows) {
  const active = rows.filter((x) => !isClosed(x));
  const count = (/** @type {string} */ t) => active.filter((x) => x.tipo === t).length;
  const critical = active.filter((x) => level(x.severidad) === "Alto" && x.tipo === "Risk");
  const stale = active.filter((x) => x.diasSinActualizar !== null && Number(x.diasSinActualizar) > 7);
  const attention = active.slice().sort((a, b) => Number(level(b.severidad) === "Alto") - Number(level(a.severidad) === "Alto") || Number(b.diasSinActualizar || 0) - Number(a.diasSinActualizar || 0));
  return {
    active,
    tiles: [
      ["layers", "Registros activos", active.length, "En el proyecto", "violet"],
      ["warning", "Riesgos activos", count("Risk"), "Amenazas por atender", "red"],
      ["clock", "Issues abiertos", count("Issue"), "Problemas existentes", "orange"],
      ["target", "Oportunidades", count("Opportunity"), "Mejoras potenciales", "green"],
      ["warning", "Críticos", critical.length, "Severidad alta", "red"],
      ["clock", "Sin seguimiento +7 días", stale.length, "Requieren revisión", "pink"],
    ],
    attention,
  };
}

/** Distribución para la dona y los avisos. @param {any[]} rows */
export function health(rows) {
  const counts = [
    ["Risk", rows.filter((x) => x.tipo === "Risk" && !isClosed(x)).length, "#ec4764"],
    ["Issue", rows.filter((x) => x.tipo === "Issue" && !isClosed(x)).length, "#ffb12d"],
    ["Opportunity", rows.filter((x) => x.tipo === "Opportunity" && !isClosed(x)).length, "#20b68a"],
    ["Cerrados", rows.filter(isClosed).length, "#bcc0d0"],
  ];
  const total = rows.length || 1;
  let pos = 0;
  /** @type {string[]} */
  const stops = [];
  counts.forEach((x) => {
    const next = pos + (100 * Number(x[1])) / total;
    if (x[1]) stops.push(`${x[2]} ${pos}% ${next}%`);
    pos = next;
  });
  const active = rows.filter((x) => !isClosed(x));
  return {
    counts,
    gradient: stops.length ? stops.join(", ") : "#e8e4f5 0 100%",
    stale: active.filter((x) => Number(x.diasSinActualizar) > 7).length,
    risks: active.filter((x) => x.tipo === "Risk").length,
    issues: active.filter((x) => x.tipo === "Issue").length,
    opportunities: active.filter((x) => x.tipo === "Opportunity").length,
    documented: active.filter((x) => level(x.impacto) && level(x.probabilidad)).length,
  };
}

/** @param {any[]} rows */
export function matrix(rows) {
  const open = rows.filter((x) => !isClosed(x));
  const valid = open.filter((x) => level(x.impacto) && level(x.probabilidad));
  const cell = (/** @type {string} */ impact, /** @type {string} */ prob) => valid.filter((x) => level(x.impacto) === impact && level(x.probabilidad) === prob).length;
  return { open: open.length, valid: valid.length, cell };
}

/** @param {any[]} rows */
export function stages(rows) {
  /** @type {Map<string, any>} */
  const map = new Map();
  rows.filter((x) => !isClosed(x)).forEach((x) => {
    const stage = iteration(x.iterationPath) || "Sin iteración";
    if (!map.has(stage)) map.set(stage, { stage, Risk: 0, Issue: 0, Opportunity: 0, total: 0 });
    const a = map.get(stage);
    a[x.tipo]++;
    a.total++;
  });
  return [...map.values()].sort((x, y) => y.total - x.total);
}

/** @param {any[]} rows */
export function people(rows) {
  /** @type {Record<string, number>} */
  const map = {};
  rows.filter((x) => !isClosed(x)).forEach((x) => {
    const p = x.asignadoA || "Sin asignar";
    map[p] = (map[p] || 0) + 1;
  });
  const list = Object.entries(map).sort((a, b) => b[1] - a[1]);
  return { list, max: list.length ? list[0][1] : 1 };
}

/** Valores únicos y ordenados de un campo, para los filtros. @param {any[]} rows @param {string} key */
export const uniqueValues = (rows, key) => [...new Set(rows.map((x) => String(x[key] || "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "es"));

/** @param {any[]} rows @param {{tipo: string, estado: string, persona: string, iter: string, q: string}} f */
export function filterRows(rows, f) {
  const q = f.q.trim().toLocaleLowerCase("es");
  return rows.filter(
    (x) =>
      (!f.tipo || x.tipo === f.tipo) &&
      (!f.estado || x.estado === f.estado) &&
      (!f.persona || x.asignadoA === f.persona) &&
      (!f.iter || iteration(x.iterationPath) === f.iter) &&
      (!q || [x.id, x.titulo, x.asignadoA, x.tipo, x.descripcion].join(" ").toLocaleLowerCase("es").includes(q)),
  );
}

/** Campos del panel de detalle según el tipo. @param {any} x */
export function detail(x) {
  const d = (x.tipo === "Risk" ? x.riskDetalle : x.tipo === "Issue" ? x.issueDetalle : x.opportunityDetalle) || {};
  const card = (/** @type {string} */ icon, /** @type {string} */ title, /** @type {any} */ value) => ({ icon, title, text: cleanHtml(value) });
  const pair = (/** @type {string} */ label, /** @type {any} */ value) => ({ label, text: cleanHtml(value) });
  if (x.tipo === "Risk") {
    return {
      kind: "RIESGO",
      aria: "Detalle del riesgo",
      left: [card("▣", "Descripción", x.descripcion), card("◎", "Plan de mitigación", d.planMitigacion), card("⚡", "Triggers", d.triggers), card("◈", "Plan de contingencia", d.contingencyPlan)],
      planningTitle: "Planning",
      planning: [pair("Prioridad", x.prioridad), pair("Severidad", x.severidad), pair("Estimación original", d.originalEstimate), pair("Fecha de seguimiento", d.fechaSeguimiento), pair("Escalar", d.escalate), pair("Persona a la que se escala", d.personaEscala), pair("Estrategia de gestión", d.estrategiaGestion)],
      secondaryTitle: "Clasificación",
      secondary: [pair("Probabilidad", x.probabilidad), pair("Impacto", x.impacto), pair("Partes interesadas", d.partesInteresadas), pair("Fuente del riesgo", d.fuenteRiesgo), pair("Categoría", d.categoria)],
    };
  }
  if (x.tipo === "Issue" || x.tipo === "Opportunity") {
    const issue = x.tipo === "Issue";
    return {
      kind: x.tipo.toUpperCase(),
      aria: `Detalle de ${issue ? "Issue" : "Opportunity"}`,
      left: issue
        ? [card("▣", "Descripción", x.descripcion), card("☷", "Plan", d.plan)]
        : [card("▣", "Descripción", x.descripcion), card("◎", "Plan de mejora", d.improvementPlan), card("⚡", "Disparadores (Triggers)", d.triggers), card("☷", "Plan de acción", d.actionPlan), card("▦", "Seguimiento", d.followUp)],
      planningTitle: issue ? "Información general" : "Planificación",
      planning: issue
        ? [pair("Prioridad", x.prioridad), pair("Escalate", d.escalate), pair("Persona a la que se escala", d.escalationContact), pair("Detection Date", d.detectionDate), pair("Reporter", d.reporter), pair("Closure Date", d.closureDate), pair("Software relacionado", d.relatedSoftware)]
        : [pair("Prioridad", x.prioridad), pair("Severidad", x.severidad), pair("Estimación original", d.originalEstimate), pair("Fecha de seguimiento", d.fechaSeguimiento), pair("Escalate", d.escalate), pair("Persona a la que se escala", d.personaEscala), pair("Estrategia de gestión", d.estrategiaGestion)],
      secondaryTitle: issue ? "Esfuerzo y análisis" : "Clasificación",
      secondary: issue
        ? [pair("Estimación original (h)", d.originalEstimate), pair("Effort completed (h)", d.effortCompleted), pair("Impacto", x.impacto), pair("Probabilidad", x.probabilidad)]
        : [pair("Probabilidad", x.probabilidad), pair("Impacto", x.impacto), pair("Partes interesadas", d.partesInteresadas), pair("Fuente de la oportunidad", d.fuenteOportunidad), pair("Categoría", d.categoria)],
    };
  }
  return null;
}
