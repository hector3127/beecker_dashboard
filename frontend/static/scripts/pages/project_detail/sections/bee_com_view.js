// @ts-check
// Centro de Comunicación: pinta la lista, el detalle y el formulario con el DOM.
import { el } from "#app/lib/dom.js";
import { TYPES, countsByType, inScope, keyPoints, kpis, projectsOf, rowSummary, visible } from "./bee_com_model.js";

const PATHS = {
  Aviso: '<path d="M3 11v2l11 4V7L3 11Z"/><path d="M14 8c3-1 5-3 7-4v16c-2-1-4-3-7-4M5 16l2 5h3l-2-6"/>',
  Lineamiento: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  "Nuevo proceso": '<path d="M10 2h4l.6 2.2 2 1.1 2.1-.8 2 3.5-1.7 1.5v2.4l1.7 1.5-2 3.5-2.1-.8-2 1.1L14 22h-4l-.6-2.2-2-1.1-2.1.8-2-3.5L5 14.5v-2.4L3.3 10.6l2-3.5 2.1.8 2-1.1L10 2Z"/><circle cx="12" cy="12" r="3"/>',
  Cambio: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  Otro: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  Importante: '<path d="M12 3 2 21h20L12 3Z"/><path d="M12 9v5M12 18h.01"/>',
};

/** Ícono del tipo (trazos fijos de este archivo, nunca datos). @param {string} type */
export function icon(type) {
  const body = /** @type {any} */ (PATHS)[type] || PATHS.Otro;
  const doc = new DOMParser().parseFromString(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`, "image/svg+xml");
  return document.importNode(doc.documentElement, true);
}

const text = (/** @type {any} */ v) => (v == null ? "" : String(v));
const NBSP_DOT = "  ·  ";

/** @param {any} x @param {(uid: string) => void} open */
function row(x, open) {
  const kind = x.importante ? "Importante" : x.categoria;
  return el(
    "button",
    { type: "button", class: "bee-com-row", onclick: () => open(x.uid) },
    el("span", { class: `bee-com-icon ${text(kind)}` }, icon(kind)),
    el(
      "span",
      { class: "copy" },
      ...(x.importante ? [el("span", { class: "bee-com-tag red", text: "Importante" }), " "] : []),
      el("span", { class: "bee-com-tag", text: text(x.categoria) }),
      el("b", { text: text(x.titulo) }),
      el("p", { text: text(rowSummary(x)) }),
      el("span", { class: "bee-com-meta", text: `▣ ${text(x.fecha)}${NBSP_DOT}♙ ${text(x.autor || "Equipo")}${NBSP_DOT}${text(x.proyecto || "Todos los proyectos")}` }),
    ),
    el("span", { text: "›" }),
  );
}

/**
 * Pinta toda la pestaña; conserva el foco de la búsqueda al escribir.
 * @param {HTMLElement} root @param {any} s @param {{filter: (key: string, value: string) => void, open: (uid: string) => void, edit: (uid?: string) => void}} h
 */
export function paintList(root, s, h) {
  const focused = document.activeElement && document.activeElement.closest(".bee-com-filters input");
  const all = inScope(s.items, s.contextProject);
  const counts = countsByType(all);
  const items = visible(all, s);
  const error = s.error ? [el("div", { class: "bee-com-card", text: s.error })] : [];
  if (error[0]) {
    error[0].style.padding = "13px";
    error[0].style.color = "#bc2449";
  }
  const empty = (/** @type {string} */ message, /** @type {string} */ tag = "p", color = "") => {
    const node = el(tag, { text: message });
    if (color) node.style.color = color;
    return node;
  };
  const search = el("input", { type: "search", placeholder: "Buscar por título o contenido…", oninput: (/** @type {Event} */ e) => h.filter("busqueda", /** @type {HTMLInputElement} */ (e.target).value) });
  /** @type {HTMLInputElement} */ (search).value = s.busqueda;
  const projectSelect = el("select", { onchange: (/** @type {Event} */ e) => h.filter("proyecto", /** @type {HTMLSelectElement} */ (e.target).value) }, el("option", { value: "", text: "Todos los proyectos" }), ...projectsOf(all).map((p) => el("option", { value: p, text: p })));
  /** @type {HTMLSelectElement} */ (projectSelect).value = s.proyecto;
  const orderSelect = el("select", { onchange: (/** @type {Event} */ e) => h.filter("orden", /** @type {HTMLSelectElement} */ (e.target).value) }, el("option", { value: "recientes", text: "Más recientes" }), el("option", { value: "antiguos", text: "Más antiguos" }));
  /** @type {HTMLSelectElement} */ (orderSelect).value = s.orden;
  const rows = (/** @type {any[]} */ list) => list.map((x) => row(x, h.open));
  const category = (/** @type {string} */ t) => {
    const badge = el("span", { class: `bee-com-icon ${t}` }, icon(t));
    badge.style.width = "25px";
    badge.style.height = "25px";
    badge.style.fontSize = "14px";
    return el("div", { class: "bee-com-category" }, badge, t, el("b", { text: String(counts[t]) }));
  };

  root.replaceChildren(
    el(
      "div",
      { class: "bee-com" },
      el("div", { class: "bee-com-head" }, el("div", { class: "bee-com-title" }, el("span", { class: "mark" }, icon("Aviso")), el("div", {}, el("h1", { text: "Centro de Comunicación" }), el("p", { text: "Avisos, lineamientos, nuevos procesos y actualizaciones importantes." }))), el("button", { type: "button", class: "bee-com-btn primary", text: "＋ Nuevo comunicado", onclick: () => h.edit() })),
      ...error,
      el("div", { class: "bee-com-kpis" }, ...kpis(all, counts).map((k) => el("div", { class: "bee-com-card bee-com-kpi" }, el("span", { class: `bee-com-icon ${k[4]}` }, icon(/** @type {string} */ (k[0]))), el("span", {}, el("b", { text: String(k[1]) }), el("strong", { text: String(k[2]) }), el("small", { text: String(k[3]) }))))),
      el(
        "div",
        { class: "bee-com-grid" },
        el(
          "section",
          { class: "bee-com-card bee-com-list" },
          el("div", { class: "bee-com-tabs" }, ...["Todos", ...TYPES].map((t) => el("button", { type: "button", class: s.tipo === t ? "active" : null, text: `${t} (${t === "Todos" ? all.length : counts[t]})`, onclick: () => h.filter("tipo", t) }))),
          el("div", { class: "bee-com-filters" }, search, projectSelect, orderSelect),
          ...(items.length ? rows(items) : [empty("No hay comunicados con estos filtros.", "p", "#747797")]),
        ),
        el(
          "aside",
          { class: "bee-com-side" },
          el("section", { class: "bee-com-card bee-com-feature" }, el("h3", { text: "⚠ Comunicados destacados" }), ...(all.filter((x) => x.importante).length ? rows(all.filter((x) => x.importante).slice(0, 2)) : [el("small", { text: "Sin comunicados destacados." })])),
          el("section", { class: "bee-com-card" }, el("h3", { text: "▤ Últimos comunicados" }), ...(all.length ? rows(all.slice(0, 4)) : [el("small", { text: "Aún no hay comunicados." })])),
          el("section", { class: "bee-com-card" }, el("h3", { text: "▤ Categorías" }), ...TYPES.map(category)),
        ),
      ),
    ),
  );
  if (focused) {
    search.focus();
    /** @type {HTMLInputElement} */ (search).setSelectionRange(s.busqueda.length, s.busqueda.length);
  }
}

/** Carga inicial. @param {HTMLElement} root */
export const paintLoading = (root) => root.replaceChildren(el("div", { class: "bee-com", text: "Cargando comunicados…" }));

/** @param {HTMLElement} node */
function overlay(node, close) {
  const modal = el("div", { id: "bee-com-modal", class: "bee-com-modal", onclick: (/** @type {Event} */ e) => e.target === modal && close() }, node);
  return modal;
}

/** @param {any} x @param {{close: () => void, edit: (uid: string) => void}} h */
export function detailModal(x, h) {
  const points = keyPoints(x.puntosClave);
  const section = (/** @type {Node} */ symbol, /** @type {string} */ title, /** @type {Node} */ body, cls = "bee-com-detail-section") => el("section", { class: cls }, el("span", { class: "symbol" }, symbol), el("div", {}, el("h3", { text: title }), body));
  return overlay(
    el(
      "div",
      { class: "bee-com-dialog bee-com-detail", role: "dialog", "aria-modal": "true", "aria-label": text(x.titulo) },
      el("div", { class: "bee-com-detail-top" }, el("span", { class: "bee-com-detail-badge" }, icon(x.categoria), ` ${text(x.categoria)}${x.importante ? " · Importante" : ""}`), el("button", { type: "button", class: "bee-com-btn", "aria-label": "Cerrar", text: "✕", onclick: h.close })),
      el("h2", { text: text(x.titulo) }),
      el("div", { class: "bee-com-detail-meta" }, el("span", { text: `▣ ${text(x.fecha)}` }), el("span", { text: `♙ ${text(x.autor || "Equipo")}` }), el("span", { text: `▱ ${text(x.proyecto || "Todos los proyectos")}` })),
      ...(x.resumen ? [el("section", { class: "bee-com-detail-summary" }, el("span", { class: "symbol", text: "ⓘ" }), el("div", {}, el("h3", { text: "Resumen" }), el("p", { text: text(x.resumen) })))] : []),
      section(icon("Lineamiento"), "Mensaje", el("div", { class: "bee-com-detail-message", text: text(x.contenido) })),
      ...(points.length ? [section(document.createTextNode("✓"), "Puntos clave", el("ol", { class: "bee-com-detail-points" }, ...points.map((t, i) => el("li", {}, el("b", { text: String(i + 1) }), el("span", { text: t })))))] : []),
      el("div", { class: "actions" }, el("button", { type: "button", class: "bee-com-btn", text: "Editar comunicado", onclick: () => h.edit(x.uid) })),
    ),
    h.close,
  );
}

/** @param {any} x @param {{contextProject: string, items: any[]}} s @param {{close: () => void, save: (e: Event, uid: string) => void}} h @param {string} uid */
export function editModal(x, s, h, uid) {
  const label = (/** @type {string} */ title, /** @type {HTMLElement} */ control) => el("label", {}, title, control);
  const input = (/** @type {string} */ name, /** @type {any} */ value, /** @type {Record<string, any>} */ extra = {}) => {
    const node = el("input", { name, ...extra });
    /** @type {HTMLInputElement} */ (node).value = text(value);
    return node;
  };
  const area = (/** @type {string} */ name, /** @type {any} */ value, /** @type {Record<string, any>} */ extra = {}) => el("textarea", { name, ...extra }, text(value));
  const projects = [...new Set([s.contextProject, ...s.items.map((a) => a.proyecto)].filter(Boolean))];
  const important = el("input", { name: "importante", type: "checkbox", checked: x.importante ? true : null });
  important.style.width = "auto";
  const importantLabel = el("label", {}, important, " Destacar como importante");
  Object.assign(importantLabel.style, { display: "flex", alignItems: "center", gap: "7px" });
  const error = el("div", { id: "bee-com-error" });
  error.style.color = "#bd274a";
  const head = el("div", {}, el("h2", { text: `${uid ? "Editar" : "Nuevo"} comunicado` }), el("button", { type: "button", class: "bee-com-btn", text: "✕", onclick: h.close }));
  head.style.display = "flex";
  head.style.justifyContent = "space-between";
  const category = el("select", { name: "categoria" }, ...TYPES.map((t) => el("option", { text: t, selected: x.categoria === t ? true : null })));
  const form = el(
    "form",
    { onsubmit: (/** @type {Event} */ e) => h.save(e, uid) },
    label("Título", input("titulo", x.titulo || "", { required: true, maxlength: 180 })),
    label("Resumen", input("resumen", x.resumen || "", { maxlength: 350 })),
    label("Contenido", area("contenido", x.contenido || "", { required: true })),
    label("Puntos clave (opcional, uno por línea)", area("puntosClave", x.puntosClave || "", { placeholder: "Escribe cada punto en una línea" })),
    label("Categoría", category),
    el("label", {}, "Proyecto (vacío = todos)", input("proyecto", x.proyecto || s.contextProject || "", { list: "bee-com-projects" }), el("datalist", { id: "bee-com-projects" }, ...projects.map((p) => el("option", { value: p })))),
    label("Publicado por", input("autor", x.autor || "")),
    importantLabel,
    error,
    el("div", { class: "actions" }, el("button", { type: "button", class: "bee-com-btn", text: "Cancelar", onclick: h.close }), el("button", { type: "submit", class: "bee-com-btn primary", text: "Publicar comunicado" })),
  );
  return overlay(el("div", { class: "bee-com-dialog", role: "dialog", "aria-modal": "true" }, head, form), h.close);
}
