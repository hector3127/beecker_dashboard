// @ts-check
// Plantillas de los comunicados (extensión, suspensión, reanudación y cierre):
// campos, validación y texto de la vista previa. El texto es el mismo que arma
// el servidor (apps/gmail/services/communique.py).

export const STAGES = ["Discovery", "Development", "Deployment"];
export const MAX_FILE = 10 * 1024 * 1024;
export const FILE_TYPE = /\.(pdf|png|jpe?g|xlsx|docx)$/i;

/** @typedef {{key: string, label: string, type: string, required?: boolean, placeholder?: string, max?: number, full?: boolean}} Field */
/** @typedef {{label: string, title: string, subtitle: string, fields: Field[], linkLabel: string, linkRequired: boolean, linkTitle: string, linkNote: string, filesTitle: string, icon: string}} Kind */

const link = (/** @type {string} */ label) => label;

/** @type {Record<string, Kind>} */
export const KINDS = {
  extension: {
    label: "Extensión",
    title: "Generar extensión de proyecto",
    subtitle: "Captura el proyecto y las fechas para generar automáticamente el comunicado de extensión.",
    icon: "clock",
    fields: [
      { key: "stage", label: "Etapa", type: "stage", required: true },
      { key: "currentDate", label: "Fecha actual de cierre", type: "date", required: true },
      { key: "newDate", label: "Nueva fecha", type: "date", required: true },
      { key: "reason", label: "Motivo de la extensión", type: "textarea", required: true, max: 500, placeholder: "Describe brevemente por qué se requiere la extensión", full: true },
    ],
    linkTitle: "Roadmap actualizado",
    linkLabel: link("Link del roadmap"),
    linkRequired: true,
    linkNote: "El roadmap se compartirá como enlace dentro del comunicado.",
    filesTitle: "Adjuntar archivos",
  },
  suspension: {
    label: "Suspensión",
    title: "Generar suspensión de proyecto",
    subtitle: "Se responde en el hilo de Inicio de proyecto, dirigida a ROC.",
    icon: "clock",
    fields: [
      { key: "stage", label: "Etapa que se detiene", type: "stage", required: true },
      { key: "resumeDate", label: "Fecha tentativa de reanudación", type: "date", required: true },
      { key: "condition", label: "Condición para reanudar", type: "text", required: true, max: 300, placeholder: "Ej. la entrega de accesos por el cliente", full: true },
      { key: "reason", label: "Motivo de la suspensión", type: "textarea", required: true, max: 500, placeholder: "Describe brevemente el motivo, contexto y situación detectada", full: true },
    ],
    linkTitle: "Enlace de soporte",
    linkLabel: link("Enlace de soporte (opcional)"),
    linkRequired: false,
    linkNote: "Si lo pones, se agrega al comunicado como enlace.",
    filesTitle: "Adjuntar archivos",
  },
  reanudacion: {
    label: "Reanudación",
    title: "Generar reanudación de proyecto",
    subtitle: "Se responde en el mismo hilo de Inicio de proyecto, dirigida a ROC.",
    icon: "clock",
    fields: [{ key: "resumeDate", label: "Fecha efectiva de reanudación", type: "date", required: true }],
    linkTitle: "Enlace de soporte",
    linkLabel: link("Enlace de soporte (opcional)"),
    linkRequired: false,
    linkNote: "Si lo pones, se agrega al comunicado como enlace.",
    filesTitle: "Adjuntar archivos",
  },
  cierre_ixb: {
    label: "Cierre",
    title: "Generar cierre de proyecto",
    subtitle: "Comunicado oficial de cierre con la MCO y el VoBo del proyecto.",
    icon: "check",
    fields: [
      { key: "projectName", label: "Nombre del proyecto", type: "text", max: 200, placeholder: "Ej. Planificación de Rutas - UNIGIS", full: true },
      { key: "closeDate", label: "Fecha de cierre", type: "date", required: true },
    ],
    linkTitle: "MCO",
    linkLabel: link("Enlace a la MCO (opcional si adjuntas el archivo)"),
    linkRequired: false,
    linkNote: "Adjunta la MCO como archivo o comparte su enlace.",
    filesTitle: "Adjuntar la MCO",
  },
  cierre_aer: {
    label: "Cierre",
    title: "Generar cierre de proyecto",
    subtitle: "Comunicado de cierre y pase del proyecto.",
    icon: "check",
    fields: [
      { key: "closeDate", label: "Fecha de cierre", type: "date", required: true },
      { key: "description", label: "Afiliado a (opcional)", type: "text", max: 180, placeholder: "Ej. las mejoras del Smart Attendance", full: true },
    ],
    linkTitle: "Enlace de soporte",
    linkLabel: link("Enlace de soporte (opcional)"),
    linkRequired: false,
    linkNote: "Si lo pones, se agrega al comunicado como enlace.",
    filesTitle: "Adjuntar archivos",
  },
};

/** Botones del selector según el tipo de proyecto. @param {string} family */
export function kindsFor(family) {
  return family === "aer" ? ["extension", "cierre_aer"] : ["extension", "suspension", "reanudacion", "cierre_ixb"];
}

/** @param {string} iso */
export function fmtDate(iso) {
  const p = String(iso || "").split("-");
  return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : "";
}

/** @param {number} hour */
export const greeting = (hour) => (hour < 12 ? "Buenos días" : "Buenas tardes");

/** @param {string} text */
const lowerFirst = (text) => (text ? text.charAt(0).toLowerCase() + text.slice(1) : text);

/**
 * Texto de la vista previa: bloques de segmentos. Un segmento es texto, {b},
 * {ph} (dato que falta) o {a} (enlace). `{road}` pinta el recuadro del roadmap.
 * @param {string} kind @param {Record<string, string>} v @param {{project: string, hasFiles: boolean, hour: number, today: string}} ctx
 * @returns {any[][]}
 */
export function previewBlocks(kind, v, ctx) {
  const ph = (/** @type {string} */ t) => ({ ph: t });
  const b = (/** @type {string} */ t, /** @type {string} */ empty) => (t ? { b: t } : ph(empty));
  const project = b(ctx.project, "[proyecto]");
  const date = (/** @type {string} */ key) => b(fmtDate(v[key]), "[fecha]");
  const support = "También se incluyen archivos de soporte con evidencias y detalles adicionales.";
  const blocks = [];
  let closing = [];
  if (kind === "extension") {
    const reason = (v.reason || "").trim();
    blocks.push(
      ["Hola estimados,"],
      ["Informo la extensión del proyecto ", project, reason ? " debido a que " + lowerFirst(reason).replace(/\.$/, "") : [" ", ph("debido a [motivo de la extensión]")], "."].flat(),
      ["Esta situación impide cerrar la etapa ", b(v.stage, "[etapa]"), " en la fecha originalmente establecida."],
      ["Fechas actualizadas:"],
      [{ li: ["Fecha actual de cierre: ", date("currentDate")] }, { li: ["Nueva fecha: ", date("newDate")] }],
      ["Adjunto el Roadmap actualizado, el cual se compartirá mediante el siguiente enlace:"],
      [{ road: (v.link || "").trim() }],
    );
    if (ctx.hasFiles) blocks.push([support]);
    closing = [["Saludos!"]];
    return [...blocks, ...closing];
  }
  if (kind === "suspension") {
    blocks.push(
      [`${greeting(ctx.hour)} ROC,`],
      ["Informo la suspensión temporal del proyecto ", project, ", debido a:"],
      [(v.reason || "").trim() || ph("[motivo de la suspensión]")],
      ["Esta situación impide continuar con la etapa ", b(v.stage, "[etapa]"), " y avanzar conforme al plan establecido."],
      ["La fecha tentativa de reanudación es ", date("resumeDate"), ", siempre que se confirme ", (v.condition || "").trim() || ph("[condición pendiente]"), "."],
    );
    closing = [["Quedamos atentos a tus comentarios o confirmación."]];
  } else if (kind === "reanudacion") {
    blocks.push(
      [`${greeting(ctx.hour)} ROC,`],
      ["Informo la reanudación del proyecto ", project, " – ya que han sido resueltos los puntos que originaron su suspensión."],
      ["La fecha efectiva de reanudación es ", date("resumeDate"), ", conforme a la coordinación establecida con el equipo operativo."],
      ["Retomamos las actividades según el plan de trabajo vigente."],
    );
    closing = [["Saludos!"]];
  } else if (kind === "cierre_ixb") {
    const name = (v.projectName || "").trim().replace(/\s+/g, " ");
    blocks.push(
      ["Hola, Buen día!"],
      ["Por este medio hago el comunicado oficial del cierre del proyecto ", project, ...(name ? [` "${name}"`] : []), " el día ", date("closeDate")],
      ["Adjunto la MCO donde podrán ver el VoBo del proyecto"],
    );
    closing = [["Quedo atento a sus comentarios,"], ["Saludos!"]];
  } else {
    const about = (v.description || "").trim().replace(/\s+/g, " ");
    const when = v.closeDate && v.closeDate === ctx.today ? ["el día de hoy - ", date("closeDate"), " -"] : ["el día ", date("closeDate")];
    blocks.push(
      ["Buen día equipo."],
      ["El presente es para dar como finalizado ", ...when, " el cierre de este proyecto ", project, ...(about ? [` - afiliado a ${about}`] : []), "."],
      ["Se hará el pase correspondiente."],
      ["Gracias a todos por su apoyo y tiempo."],
    );
    closing = [["Saludos cordiales."]];
  }
  const url = (v.link || "").trim();
  if (url) blocks.push([kind === "cierre_ixb" ? "MCO: " : "Enlace de soporte: ", { a: url }]);
  if (ctx.hasFiles) blocks.push([kind === "cierre_ixb" ? "La MCO se incluye como archivo adjunto." : support]);
  return [...blocks, ...closing];
}

/** Asunto de la vista previa. @param {{subject: string} | undefined} thread */
export function previewSubject(thread) {
  return thread ? "Re: " + thread.subject.replace(/^\s*(re|rv)\s*:\s*/i, "") : "Selecciona un hilo de Gmail";
}

/**
 * Primer dato que falta, con el mismo orden de la pantalla anterior.
 * @param {string} kind @param {Record<string, string>} v @param {string} project @param {number} files
 * @returns {string} mensaje, o cadena vacía
 */
export function missingField(kind, v, project, files) {
  const spec = KINDS[kind];
  if (!project.trim()) return "Falta el proyecto.";
  const noun = (/** @type {Field} */ f) => (kind === "extension" ? { stage: "la etapa", currentDate: "la fecha actual de cierre", newDate: "la nueva fecha", reason: "el motivo" }[f.key] : { stage: "la etapa", resumeDate: "la fecha de reanudación", condition: "la condición pendiente", reason: "el motivo", closeDate: "la fecha de cierre" }[f.key]) || f.label.toLowerCase();
  const order = kind === "extension" ? ["stage", "currentDate", "newDate", "reason"] : spec.fields.map((f) => f.key);
  for (const key of order) {
    const field = spec.fields.find((f) => f.key === key);
    if (field && field.required && !(v[key] || "").trim()) return `Falta ${noun(field)}.`;
  }
  if (spec.linkRequired && !(v.link || "").trim()) return "Falta el link del roadmap.";
  if (kind === "cierre_ixb" && !(v.link || "").trim() && !files) return "Adjunta la MCO como archivo o pon su enlace.";
  return "";
}

/**
 * Campos que se envían al servidor.
 * @param {string} kind @param {Record<string, string>} v @param {string} project @param {string} threadId
 * @returns {[string, string][]}
 */
export function payload(kind, v, project, threadId) {
  /** @type {[string, string][]} */
  const out = [["kind", kind], ["project", project.trim()], ["threadId", threadId]];
  for (const f of KINDS[kind].fields) {
    const raw = (v[f.key] || "").trim();
    if (f.key === "description" && raw) out.push([f.key, "a " + raw.replace(/^a\s+/i, "")]);
    else if (raw || f.required) out.push([f.key, raw]);
  }
  const url = (v.link || "").trim();
  if (url) out.push([kind === "extension" ? "roadmapLink" : "link", url]);
  return out;
}
