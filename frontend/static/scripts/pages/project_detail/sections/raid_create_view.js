// @ts-check
// Ventana de alta RAID y su formulario por tipo (riesgo, issue, oportunidad).
// Todo se construye con el DOM; los valores solo entran como texto o value.
import { el } from "#app/lib/dom.js";
import { COPY, SUGGEST_KEYS, parentStatus, planLines, suggestions } from "./raid_create_model.js";
import { TYPES, severityNumber } from "./raid_model.js";

const $ = (/** @type {string} */ id) => /** @type {HTMLElement | null} */ (document.getElementById(id));

/** Control de texto, número, fecha, área de texto o lista con opciones reales de Azure. @param {string} key @param {string} label @param {string} type @param {any} value @param {any[]} [options] */
function field(key, label, type, value, options) {
  const text = value == null ? "" : String(value);
  const opts = Array.isArray(options) ? options : [];
  if (opts.length) {
    const valid = opts.some((x) => String(x) === text);
    const select = el("select", { "data-raid-key": key }, el("option", { value: "", text: text && !valid ? "Elige un valor válido de Azure" : "Sin especificar" }), ...opts.map((x) => el("option", { value: String(x), selected: String(x) === text || null, text: String(x) })));
    const hint = text && !valid ? [el("small", { text: `Claude sugirió «${text}»; elige una opción real de Azure.` })] : [];
    if (hint[0]) hint[0].style.color = "#c47e12";
    return el("label", {}, label, select, ...hint);
  }
  if (type === "textarea") {
    const area = el("textarea", { "data-raid-key": key, rows: 3 }, text);
    return el("label", {}, label, area);
  }
  const input = el("input", { "data-raid-key": key, type: type || "text" });
  /** @type {HTMLInputElement} */ (input).value = text;
  return el("label", {}, label, input);
}

/** Lista simple "Sin especificar" + opciones, o texto libre si Azure no dio opciones. @param {string} key @param {string} label @param {any} value @param {any[]} [items] */
function pick(key, label, value, items) {
  const v = String(value || "");
  const arr = Array.isArray(items) ? items : [];
  if (!arr.length) return field(key, label, "text", v);
  return el("label", {}, label, el("select", { "data-raid-key": key }, el("option", { value: "", text: "Sin especificar" }), ...arr.map((x) => el("option", { value: String(x), selected: String(x) === v || null, text: String(x) }))));
}

/** Campo con buscador de sugerencias de Azure. @param {string} key @param {string} label @param {any} value @param {string} help */
function suggestField(key, label, value, help) {
  const input = el("input", { type: "text", "data-raid-key": key, id: "ixs-raid-alta-" + key, autocomplete: "off", placeholder: help || "Buscar…" });
  /** @type {HTMLInputElement} */ (input).value = value || "";
  const hints = [];
  if (key === "iterationPath") hints.push(el("small", { text: "Solo rutas reales de este proyecto Azure. Por defecto: raíz del proyecto." }));
  if (key === "relatedWorkItemId") hints.push(el("small", { id: "ixs-raid-parent-status", role: "status", "aria-live": "polite", text: "Sin padre seleccionado. El nuevo registro quedará como Child del padre que elijas." }));
  return el("label", {}, label, el("span", { class: "ixs-raid-suggest-wrap" }, input, el("span", { class: "ixs-raid-autocomplete", id: "ixs-raid-alta-list-" + key, hidden: true })), ...hints);
}

/** Campo calculado de solo lectura. @param {string} key @param {string} label @param {string} value */
function derived(key, label, value) {
  const input = el("input", { type: "text", "data-raid-key": key, readonly: true, placeholder: "Selecciona Severity" });
  /** @type {HTMLInputElement} */ (input).value = value || "";
  input.style.background = "#f7f4ff";
  input.style.color = "#4d389d";
  return el("label", {}, label, input, el("small", { text: "Se calcula automáticamente desde el número de Severity." }));
}

/** @param {string} icon @param {string} title @param {...any} body */
const card = (icon, title, ...body) => el("section", { class: "ixs-raid-risk-card" }, el("h4", {}, el("span", { text: icon }), title), ...body);
const meta = (/** @type {any[]} */ items) => el("div", { class: "ixs-raid-risk-meta" }, ...items);
const column = (/** @type {any[]} */ ...items) => el("div", { class: "ixs-raid-risk-column" }, ...items);

/**
 * Ventana y sus controles; las acciones las decide el controlador.
 * @param {string} tipo @param {string} project @param {Record<string, any>} h
 */
export function createModal(tipo, project, h) {
  const t = /** @type {any} */ (TYPES)[tipo];
  const copy = COPY[tipo];
  const risk = tipo === "Risk";
  const head = el("header", {}, el("b", { text: `${t.icon} NEW ${tipo.toUpperCase()} · ${project}` }), el("button", { type: "button", "aria-label": "Cerrar", text: "✕", onclick: h.close }));
  head.style.setProperty("--raid-color", t.color);
  const free = el("textarea", { id: "ixs-raid-free", rows: 4, placeholder: "Escribe aquí la situación observada…" });
  const promptBox = el("textarea", { id: "ixs-raid-prompt", rows: risk ? 4 : 14, placeholder: risk ? "Instrucciones adicionales (opcionales)" : "Cargando prompt estándar…" });
  const actions = el("div", {}, el("button", { type: "button", class: "ixs-btn", text: risk ? "Guardar instrucciones" : "Guardar prompt", onclick: (/** @type {Event} */ e) => h.savePrompt(/** @type {HTMLButtonElement} */ (e.currentTarget)) }), ...(risk ? [] : [el("button", { type: "button", class: "ixs-btn", text: "Restaurar estándar", onclick: (/** @type {Event} */ e) => h.restorePrompt(/** @type {HTMLButtonElement} */ (e.currentTarget)) })]));
  Object.assign(actions.style, { display: "flex", alignItems: "center", gap: "7px", flexWrap: "wrap", marginTop: "8px" });
  const intro = el(
    "div",
    { id: "ixs-raid-ai-intro" },
    el("p", { text: `${copy.intro} Podrás editar todo antes de publicarlo en Azure DevOps.` }),
    el("label", {}, `Describe el ${copy.noun} con tus palabras`, free),
    el("p", { class: "ixs-raid-muted", id: "ixs-raid-api-state", text: "Verificando conexión con Claude…" }),
    el(
      "details",
      { class: "ixs-raid-prompt" },
      el("summary", { text: `✎ ${risk ? "Personalizar instrucciones de riesgo" : "Ver / personalizar prompt estándar de " + t.label.toLowerCase()}` }),
      promptBox,
      actions,
      el("small", { text: risk ? "Instrucciones adicionales del generador de riesgo existente." : "Issue y Opportunity tienen prompts independientes. Si lo editas, se guarda solo para tu usuario. Restaurar estándar recupera el texto original." }),
    ),
  );
  const form = el("div", { id: "ixs-raid-form-wrap" });
  form.style.display = "none";
  const create = el("button", { type: "button", id: "ixs-raid-create", class: "ixs-btn primary", text: "Crear en Azure DevOps", onclick: (/** @type {Event} */ e) => h.create(/** @type {HTMLButtonElement} */ (e.currentTarget)) });
  create.style.display = "none";
  const overlay = el(
    "div",
    { id: "ixs-raid-modal", class: "ixs-raid-modal-overlay", onclick: (/** @type {Event} */ e) => e.target === overlay && h.close() },
    el(
      "div",
      { class: "ixs-raid-modal ixs-raid-risk-modal", role: "dialog", "aria-modal": "true", "aria-label": `Crear ${t.label}` },
      head,
      el("div", { class: "ixs-raid-modal-content" }, intro, form, el("div", { id: "ixs-raid-modal-msg", role: "status" })),
      el("footer", {}, el("button", { type: "button", class: "ixs-btn", text: "Cancelar", onclick: h.close }), el("button", { type: "button", id: "ixs-raid-manual", class: "ixs-btn", text: "✎ Llenar manualmente", onclick: h.manual }), el("button", { type: "button", id: "ixs-raid-suggest", class: "ixs-btn primary", text: "✨ Sugerir con IA", onclick: (/** @type {Event} */ e) => h.suggest(/** @type {HTMLButtonElement} */ (e.currentTarget)) }), create),
    ),
  );
  return overlay;
}

/** @param {string} text @param {boolean} [bad] */
export function message(text, bad = false) {
  const node = $("ixs-raid-modal-msg");
  if (!node) return;
  node.textContent = text || "";
  node.style.color = bad ? "#c92e50" : "#278962";
}

/** Línea de estado del padre según lo escrito. @param {any} cfg */
export function paintParent(cfg) {
  const input = /** @type {HTMLInputElement | null} */ ($("ixs-raid-alta-relatedWorkItemId"));
  const out = $("ixs-raid-parent-status");
  if (!input || !out) return;
  const s = parentStatus(input.value, cfg);
  out.textContent = s.text;
  out.style.color = s.color;
}

/** Sugerencias del campo con buscador. @param {string} key @param {() => any} getCfg */
function openSuggestions(key, getCfg) {
  const input = /** @type {HTMLInputElement | null} */ ($("ixs-raid-alta-" + key));
  const list = $("ixs-raid-alta-list-" + key);
  if (!input || !list) return;
  const options = suggestions(key, getCfg());
  const query = input.value.trim().toLowerCase();
  const choices = (query ? options.filter((x) => x.keywords.includes(query)) : options).slice(0, 9);
  if (!options.length) {
    list.hidden = true;
    list.replaceChildren();
    return;
  }
  list.replaceChildren(
    ...(choices.length
      ? choices.map((o) => {
          const button = el("button", { class: "ixs-raid-option", type: "button", text: o.text });
          button.addEventListener("mousedown", (ev) => {
            ev.preventDefault(); // elegir antes del blur, como en el generador de riesgos
            input.value = o.value;
            input.dataset.raidChosen = "1";
            list.hidden = true;
            input.dispatchEvent(new Event("change", { bubbles: true }));
          });
          return button;
        })
      : [el("span", { class: "ixs-raid-suggest-empty", text: "Sin coincidencias. Revisa la búsqueda." })]),
  );
  list.hidden = false;
}

/** Cambia a lista los campos que Azure ya dio con opciones reales, sin borrar lo escrito. @param {any} ctx */
export function refreshOptions(ctx) {
  const form = $("ixs-raid-form-wrap");
  if (!form || form.style.display === "none") return;
  const opts = ctx.options || {};
  const iteration = /** @type {HTMLInputElement | null} */ (form.querySelector('[data-raid-key="iterationPath"]'));
  if (iteration && (!iteration.value.trim() || iteration.dataset.raidAutoRoot === "1" || (iteration.value.trim() === ctx.project && opts.proyectoAzure && opts.proyectoAzure !== ctx.project))) {
    iteration.value = opts.iteracionDefault || opts.proyectoAzure || "";
    iteration.dataset.raidAutoRoot = "1";
  }
  const mapped = /** @type {Record<string, string>} */ ({ estrategiaGestion: "managementStrategy", partesInteresadas: "stakeholders", fuenteOportunidad: "opportunitySource", fuenteRiesgo: "riskSource", categoria: "category" });
  ["state", "reason", "escalate", "relatedSoftware", "estrategiaGestion", "partesInteresadas", "fuenteOportunidad", "fuenteRiesgo", "categoria", "severidad", "prioridad", "probabilidad"].forEach((key) => {
    const node = /** @type {HTMLInputElement | null} */ (form.querySelector(`[data-raid-key="${key}"]`));
    const info = (opts.campos || {})[mapped[key] || key] || (ctx.fieldTypes || {})[key];
    if (!node || !info || !Array.isArray(info.opciones) || !info.opciones.length || node.tagName === "SELECT") return;
    const prev = node.value;
    const select = el("select", { "data-raid-key": key }, el("option", { value: "", text: "Sin especificar" }), ...info.opciones.map((/** @type {any} */ v) => el("option", { value: String(v), text: String(v) })));
    const first = (/** @type {any} */ v) => (String(v).match(/^\d+/) || [])[0];
    const matched = info.opciones.find((/** @type {any} */ v) => String(v) === prev) ?? (key === "severidad" ? info.opciones.find((/** @type {any} */ v) => first(v) === first(prev)) : null);
    if (matched !== undefined && matched !== null) /** @type {HTMLSelectElement} */ (select).value = String(matched);
    else if (prev) {
      select.prepend(el("option", { value: prev, text: prev }));
      /** @type {HTMLSelectElement} */ (select).value = prev;
    }
    node.replaceWith(select);
  });
}

/** Activa buscadores y calculados del formulario recién construido. @param {any} ctx */
function wire(out, tipo, ctx) {
  // Un solo escuchador en el formulario: sigue funcionando si Azure cambia el
  // campo de Severidad a lista después de pintarlo.
  const sync = () => {
    const severity = /** @type {HTMLInputElement | null} */ (out.querySelector('[data-raid-key="severidad"]'));
    if (!severity) return;
    const n = severityNumber(severity.value);
    const impact = /** @type {HTMLInputElement | null} */ (out.querySelector('[data-raid-key="impactoNivel"]'));
    if (impact) impact.value = n;
    if (out.dataset.tipo === "Issue") {
      const prob = /** @type {HTMLInputElement | null} */ (out.querySelector('[data-raid-key="probabilidad"]'));
      if (prob) prob.value = n;
    }
  };
  out.dataset.tipo = tipo;
  if (!out.dataset.syncing) {
    out.dataset.syncing = "1";
    const onChange = (/** @type {Event} */ e) => /** @type {HTMLElement} */ (e.target).dataset?.raidKey === "severidad" && sync();
    out.addEventListener("input", onChange);
    out.addEventListener("change", onChange);
  }
  sync();
  SUGGEST_KEYS.forEach((key) => {
    const input = /** @type {HTMLInputElement | null} */ ($("ixs-raid-alta-" + key));
    const list = $("ixs-raid-alta-list-" + key);
    if (!input || !list) return;
    input.addEventListener("input", () => {
      input.dataset.raidChosen = "";
      openSuggestions(key, () => ctx.options);
      if (key === "relatedWorkItemId") paintParent(ctx.options);
    });
    input.addEventListener("change", () => key === "relatedWorkItemId" && paintParent(ctx.options));
    input.addEventListener("focus", () => openSuggestions(key, () => ctx.options));
    input.addEventListener("blur", () => setTimeout(() => (list.hidden = true), 220));
  });
  paintParent(ctx.options);
}

/**
 * Formulario del tipo, con lo sugerido o escrito (`s`). Conserva responsable,
 * iteración y vínculo si se vuelve a sugerir.
 * @param {string} tipo @param {Record<string, any>} s @param {{project: string, options: any, fieldTypes: any}} ctx
 */
export function buildForm(tipo, s, ctx) {
  const out = $("ixs-raid-form-wrap");
  if (!out) return;
  const issue = tipo === "Issue";
  const risk = tipo === "Risk";
  const typed = /** @type {Record<string, string>} */ ({});
  if (out.style.display !== "none") out.querySelectorAll("[data-raid-key]").forEach((f) => (typed[/** @type {HTMLElement} */ (f).dataset.raidKey || ""] = /** @type {HTMLInputElement} */ (f).value));
  ["responsable", "iterationPath", "relatedWorkItemId", "reporter", "escalationContact", "personaEscala"].forEach((k) => {
    if (typed[k] && !s[k]) s[k] = typed[k];
  });
  const cfg = ctx.options || {};
  const list = (/** @type {string} */ k) => ((ctx.fieldTypes || {})[k] || {}).opciones || [];
  const cfgList = (/** @type {string} */ k, /** @type {any[]} */ fallback = []) => ((cfg.campos || {})[k] || {}).opciones || fallback;
  const sev = s.nivel || s.severidad || "";
  const number = severityNumber(sev);
  const free = /** @type {HTMLTextAreaElement | null} */ ($("ixs-raid-free"));
  /** @type {Record<string, HTMLElement>} */
  const f = {};
  f.titulo = field("titulo", "Título *", "text", s.titulo);
  f.descripcion = field("descripcion", "Descripción *", "textarea", s.descripcion || (free ? free.value : ""));
  const responsable = suggestField("responsable", "Responsable (sugerencias Azure)", s.responsable, "Buscar nombre o correo…");
  const iterationValue = s.iterationPath || cfg.iteracionDefault || cfg.proyectoAzure || ctx.project;
  f.responsable = responsable;
  f.iterationPath = suggestField("iterationPath", "Iteration Path (proyecto / etapa)", iterationValue, "Buscar iteración real…");
  f.severidad = field("severidad", "Severidad", "text", sev, list("severidad"));
  f.prioridad = field("prioridad", "Prioridad", "text", s.prioridad || "", list("prioridad"));
  f.probabilidad = issue ? derived("probabilidad", "Probabilidad (= Severity)", number) : field("probabilidad", "Probabilidad", "text", risk ? s.probabilidad || s.prioridad || "" : s.probabilidad, list("probabilidad"));
  f.impactoNivel = derived("impactoNivel", "Impacto (= Severity)", number);
  const related = (/** @type {string} */ help) => suggestField("relatedWorkItemId", "Work Item PADRE (ID o título)", s.relatedWorkItemId, help);
  const relation = () => card("↗", "Related Work", el("div", { class: "ixs-raid-form-section", text: "Relación Parent → Child · el registro que crearás será hijo del WI seleccionado" }), related("Escribe #132790 o busca el WI padre…"));
  const head = (/** @type {string} */ text, /** @type {string} */ small = "") => el("div", { class: "ixs-raid-form-head" }, el("b", { text: `${text} · ${ctx.project}` }), ...(small ? [el("small", { text: small })] : []));
  let body;
  if (risk) {
    Object.assign(f, {
      planMitigacion: field("planMitigacion", "Plan de mitigación", "textarea", s.planMitigacion),
      triggers: field("triggers", "Triggers / señales", "textarea", s.triggers),
      contingencyPlan: field("contingencyPlan", "Plan de contingencia", "textarea", s.contingencyPlan),
      categoria: pick("categoria", "Categoría", s.categoria, list("categoria")),
      fuenteRiesgo: pick("fuenteRiesgo", "Fuente del riesgo", s.fuenteRiesgo, list("fuenteRiesgo")),
      estrategiaGestion: pick("estrategiaGestion", "Estrategia de gestión", s.estrategiaGestion, list("estrategiaGestion")),
      partesInteresadas: pick("partesInteresadas", "Partes interesadas", s.partesInteresadas, list("partesInteresadas")),
      personaEscala: suggestField("personaEscala", "Persona a la que se escala", s.personaEscala, "Buscar persona en Azure…"),
      escalate: pick("escalate", "¿Escalar? (Sí / No)", s.escalate || "No", list("escalate")),
      fechaSeguimiento: field("fechaSeguimiento", "Fecha de seguimiento", "date", s.fechaSeguimiento),
      relatedWorkItemId: related("Buscar WI padre…"),
    });
    body = [
      head("Nuevo riesgo", "Revisa los campos antes de crear en Azure DevOps"),
      el(
        "div",
        { class: "ixs-raid-risk-form" },
        column(card("▣", "Descripción", f.descripcion), card("◎", "Plan de mitigación", f.planMitigacion), card("⚡", "Triggers", f.triggers), card("◈", "Plan de contingencia", f.contingencyPlan)),
        column(
          card("▦", "Datos generales y planificación", meta([f.titulo, f.responsable, f.iterationPath, f.severidad, f.prioridad, f.escalate, f.personaEscala, f.estrategiaGestion, f.fechaSeguimiento])),
          card("▥", "Clasificación", meta([f.probabilidad, f.impactoNivel, f.partesInteresadas, f.fuenteRiesgo, f.categoria, f.relatedWorkItemId])),
        ),
      ),
    ];
  } else if (issue) {
    Object.assign(f, {
      planMitigacion: field("planMitigacion", "Plan de mitigación → Corrective Action Plan (Azure) · una acción por línea", "textarea", planLines(s.planMitigacion)),
      state: pick("state", "State (opcional, Azure define el valor inicial)", s.state, cfgList("state")),
      reason: pick("reason", "Reason (opcional; depende del State)", s.reason, cfgList("reason")),
      escalate: pick("escalate", "Escalate", s.escalate || "No", cfgList("escalate", ["No", "Yes"])),
      escalationContact: suggestField("escalationContact", "Persona a la que se escala (Escalation Contact)", s.escalationContact, "Buscar persona en Azure…"),
      detectionDate: field("detectionDate", "Detection Date (fecha de detección, si existe en Azure)", "date", s.detectionDate),
      reporter: suggestField("reporter", "Persona que reporta (Reporter)", s.reporter, "Buscar persona en Azure…"),
      closureDate: field("closureDate", "Closure Date", "date", s.closureDate),
      relatedSoftware: pick("relatedSoftware", "Software relacionado (Related Software)", s.relatedSoftware || "", cfgList("relatedSoftware")),
      originalEstimate: field("originalEstimate", "Original Estimate (h)", "number", s.originalEstimate),
      effortCompleted: field("effortCompleted", "Effort completed (h)", "number", s.effortCompleted),
    });
    body = [
      head("Nuevo Issue"),
      el(
        "div",
        { class: "ixs-raid-risk-form" },
        column(card("▣", "Description", f.descripcion), card("☷", "Plan", f.planMitigacion)),
        column(
          card("▦", "General Information", meta([f.titulo, f.responsable, f.iterationPath, f.severidad, f.prioridad, f.state, f.reason, f.escalate, f.escalationContact, f.detectionDate, f.reporter, f.closureDate, f.relatedSoftware])),
          card("◷", "Effort (Hours)", meta([f.originalEstimate, f.effortCompleted, f.probabilidad, f.impactoNivel])),
          relation(),
        ),
      ),
    ];
  } else {
    Object.assign(f, {
      planAprovechamiento: field("planAprovechamiento", "Plan de aprovechamiento", "textarea", s.planAprovechamiento),
      senalAlerta: field("senalAlerta", "Señal de alerta", "textarea", s.senalAlerta),
      planAccion: field("planAccion", "Action plan · Plan de acción", "textarea", s.planAccion),
      followUp: field("followUp", "Follow up · Seguimiento", "textarea", s.followUp),
      originalEstimate: field("originalEstimate", "Original Estimate (h)", "number", s.originalEstimate),
      fechaSeguimiento: field("fechaSeguimiento", "Fecha de seguimiento", "datetime-local", s.fechaSeguimiento),
      escalate: pick("escalate", "Escalate", s.escalate, cfgList("escalate")),
      personaEscala: suggestField("personaEscala", "Persona a la que se escala", s.personaEscala, "Buscar persona en Azure…"),
      estrategiaGestion: pick("estrategiaGestion", "Estrategia de gestión", s.estrategiaGestion, cfgList("managementStrategy")),
      partesInteresadas: pick("partesInteresadas", "Partes interesadas afectadas", s.partesInteresadas, cfgList("stakeholders")),
      fuenteOportunidad: pick("fuenteOportunidad", "Fuente de la oportunidad", s.fuenteOportunidad, cfgList("opportunitySource")),
      categoria: pick("categoria", "Categoría", s.categoria, cfgList("category")),
      state: pick("state", "State (opcional; Azure define el inicial)", s.state, cfgList("state")),
      reason: pick("reason", "Reason (opcional; depende del State)", s.reason, cfgList("reason")),
    });
    body = [
      head("Nueva oportunidad"),
      el(
        "div",
        { class: "ixs-raid-risk-form" },
        column(card("▣", "Descripción", f.descripcion), card("◎", "Plan de mejora", f.planAprovechamiento), card("⚡", "Disparadores (Triggers)", f.senalAlerta), card("☷", "Plan de acción", f.planAccion), card("▦", "Seguimiento", f.followUp)),
        column(
          card("▦", "Planificación", meta([f.titulo, f.responsable, f.iterationPath, f.severidad, f.prioridad, f.originalEstimate, f.fechaSeguimiento, f.escalate, f.personaEscala, f.estrategiaGestion])),
          card("▥", "Clasificación", meta([f.probabilidad, f.impactoNivel, f.partesInteresadas, f.fuenteOportunidad, f.categoria, f.state, f.reason])),
          relation(),
        ),
      ),
    ];
  }
  out.style.display = "block";
  out.replaceChildren(...body);
  wire(out, tipo, ctx);
  refreshOptions(ctx);
  const create = $("ixs-raid-create");
  if (create) create.style.display = "";
}
