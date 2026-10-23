// @ts-check
// Pestaña Gestión RAID: construye el DOM (sin innerHTML) y no guarda estado.
import { el } from "#app/lib/dom.js";
import { dateText } from "./ixs_executive_model.js";
import { icon } from "./ixs_icons.js";
import { statusClass } from "./ixs_planning_azure.js";
import { detail, health, iteration, level, matrix, people, safeLink, stages, summary, typeOf } from "./raid_model.js";

const empty = (/** @type {string} */ text, /** @type {string} */ [color] = [""]) => {
  const node = el("div", { class: "ixs-azure-empty", text });
  if (color) node.style.color = color;
  return node;
};
const section = (/** @type {string} */ ico, /** @type {string} */ title, /** @type {any[]} */ ...rest) => el("div", { class: "ixs-section-head" }, el("h3", {}, icon(ico), ` ${title}`), ...rest);

/** @param {any} row */
function typeBadge(row) {
  const t = typeOf(row);
  const node = el("span", { class: "ixs-raid-pill", text: `${t.icon} ${t.label}` });
  node.style.setProperty("--raid-color", t.color);
  return node;
}
/** @param {any} row */
const statusBadge = (row) => el("span", { class: `ixs-azure-badge ${statusClass(row.estado)}`, text: row.estado || "—" });
/** @param {any} x */
const azureLink = (x, text = `#${x.id}`) => el("a", { href: safeLink(x.url), target: "_blank", rel: "noopener noreferrer", text });

/** Estructura fija de la pestaña. @param {{create: (type: string) => void, sync: () => void, toggle: (b: HTMLElement) => void, filter: () => void}} h */
export function buildShell(h) {
  const newButton = (/** @type {string} */ cls, /** @type {string} */ text, /** @type {string} */ type) => el("button", { type: "button", class: `ixs-raid-new ${cls}`, text, onclick: () => h.create(type) });
  const select = (/** @type {string} */ id, /** @type {string} */ first, /** @type {[string, string][]} */ options = []) =>
    el("select", { id, onchange: h.filter }, el("option", { value: "", text: first }), ...options.map(([value, text]) => el("option", { value, text })));
  const warning = el("div", { id: "ixs-raid-sync-warning", class: "ixs-raid-info", hidden: true });
  const loading = (/** @type {string} */ id, /** @type {string} */ text = "Consultando…") => el("div", { id, class: "ixs-azure-empty", text });
  const attentionButton = el("button", { type: "button", class: "ixs-btn", id: "ixs-raid-att-btn", hidden: true, onclick: (/** @type {Event} */ e) => h.toggle(/** @type {HTMLElement} */ (e.currentTarget)) });
  return el(
    "div",
    { class: "ixs-raid-dashboard" },
    el(
      "section",
      { class: "ixs-card ixs-raid-hero" },
      el(
        "div",
        { class: "ixs-raid-hero-head" },
        el("div", { class: "ixs-raid-heading" }, el("span", { class: "ixs-raid-hero-icon" }, icon("target")), el("div", {}, el("h2", { text: "Gestión de riesgos y oportunidades" }), el("p", { text: "Radar del proyecto · Riesgos, Issues y oportunidades registrados en Azure DevOps." }))),
        el("div", { class: "ixs-raid-hero-actions" }, el("button", { type: "button", class: "ixs-btn", onclick: h.sync }, icon("refresh"), " Sincronizar"), newButton("risk", "+ Riesgo", "Risk"), newButton("issue", "+ Issue", "Issue"), newButton("opportunity", "+ Oportunidad", "Opportunity")),
      ),
      el("div", { class: "ixs-raid-info", text: "ⓘ Cada tipo tiene su propio formulario y prompt de Claude. La IA solo sugiere: nada se publica en Azure hasta que pulses «Crear en Azure»." }),
    ),
    warning,
    el("div", { id: "ixs-raid-kpis", class: "ixs-raid-kpis" }, el("div", { class: "ixs-card ixs-azure-empty", text: "Consultando registros del proyecto…" })),
    el(
      "div",
      { class: "ixs-raid-top" },
      el("section", { class: "ixs-card" }, section("warning", "Atención prioritaria", attentionButton), loading("ixs-raid-atencion", "Consultando registros…")),
      el("section", { class: "ixs-card" }, section("donut", "Distribución y severidad"), loading("ixs-raid-health", "Consultando distribución…")),
    ),
    el(
      "section",
      { class: "ixs-card" },
      section("layers", "Registro unificado — Azure DevOps", el("small", { id: "ixs-raid-count", text: "Riesgos, Issues y oportunidades" })),
      el(
        "div",
        { class: "ixs-raid-filters" },
        select("ixs-raid-filter-tipo", "Todos los tipos", [["Risk", "Riesgos"], ["Issue", "Issues"], ["Opportunity", "Oportunidades"]]),
        select("ixs-raid-filter-estado", "Todos los estados"),
        select("ixs-raid-filter-persona", "Todos los responsables"),
        select("ixs-raid-filter-iteracion", "Todas las iteraciones"),
        el("input", { id: "ixs-raid-filter-search", type: "search", placeholder: "Buscar título, ID, persona…", oninput: h.filter }),
      ),
      loading("ixs-raid-tabla", "Consultando registros…"),
    ),
    el(
      "div",
      { class: "ixs-raid-bottom" },
      el("section", { class: "ixs-card" }, section("chart", "Matriz riesgo / oportunidad"), loading("ixs-raid-matrix")),
      el("section", { class: "ixs-card" }, section("layers", "Abiertos por etapa / iteración"), loading("ixs-raid-etapas")),
      el("section", { class: "ixs-card" }, section("people", "Carga por responsable"), loading("ixs-raid-personas")),
    ),
    el("p", { id: "ixs-raid-notice", class: "ixs-raid-footnote" }),
  );
}

/** @param {HTMLElement} root @param {string} id */
const $ = (root, id) => /** @type {HTMLElement} */ (root.querySelector("#" + id));

/** Mientras consulta o si falla. @param {HTMLElement} root @param {string} text @param {string} [color] */
export function fillSections(root, text, color = "") {
  ["ixs-raid-kpis", "ixs-raid-atencion", "ixs-raid-health", "ixs-raid-tabla", "ixs-raid-matrix", "ixs-raid-etapas", "ixs-raid-personas"].forEach((id) => {
    const node = root.querySelector("#" + id);
    if (node) node.replaceChildren(empty(text, [color]));
  });
}

/** @param {HTMLElement} root @param {any[]} rows @param {{detail: (id: number) => void}} h */
export function paintSummary(root, rows, h) {
  const { tiles, attention } = summary(rows);
  $(root, "ixs-raid-kpis").replaceChildren(
    ...tiles.map((x) => el("div", { class: `ixs-raid-stat ${x[4]}` }, el("div", { class: "ixs-raid-stat-icon" }, icon(/** @type {string} */ (x[0]))), el("div", { class: "meta" }, el("label", { text: String(x[1]) }), el("b", { text: String(x[2]) }), el("small", { text: String(x[3]) })))),
  );
  const box = $(root, "ixs-raid-atencion");
  box.dataset.open = "";
  box.replaceChildren(
    ...(attention.length
      ? [
          el(
            "div",
            { class: "ixs-raid-att-list" },
            ...attention.map((x, i) => {
              const title = el("span", { class: "ixs-raid-att-title", role: "button", tabindex: "0", text: x.titulo == null ? "" : String(x.titulo), onclick: () => h.detail(Number(x.id)) });
              title.addEventListener("keydown", (e) => e.key === "Enter" && h.detail(Number(x.id)));
              return el("div", { class: "ixs-raid-att-row", hidden: i >= 4 || null, "data-raid-extra": i >= 4 ? "" : null }, azureLink(x), title, typeBadge(x), el("small", { text: x.asignadoA == null ? "" : String(x.asignadoA) }), el("b", { class: "ixs-raid-days", text: `${Number(x.diasSinActualizar) || 0} d` }));
            }),
          ),
        ]
      : [empty("Sin registros abiertos que requieran seguimiento.")]),
  );
  const more = $(root, "ixs-raid-att-btn");
  more.hidden = attention.length <= 4;
  more.textContent = `Ver más (${Math.max(0, attention.length - 4)})`;
}

/** @param {HTMLElement} box @param {HTMLElement} button @param {number} total */
export function toggleAttention(box, button, total) {
  const open = box.dataset.open === "1";
  box.dataset.open = open ? "0" : "1";
  box.querySelectorAll("[data-raid-extra]").forEach((row) => {
    /** @type {HTMLElement} */ (row).hidden = open;
  });
  button.textContent = open ? `Ver más (${Math.max(0, total - 4)})` : "Ver menos";
}

/** @param {HTMLElement} root @param {any[]} rows */
export function paintHealth(root, rows) {
  const h = health(rows);
  const donut = el("div", { class: "ixs-raid-donut" }, el("div", {}, el("b", { text: String(rows.length) }), el("small", { text: "registros" })));
  donut.style.background = `conic-gradient(${h.gradient})`;
  $(root, "ixs-raid-health").replaceChildren(
    el(
      "div",
      { class: "ixs-raid-health" },
      donut,
      el(
        "div",
        { class: "ixs-raid-health-legend" },
        ...h.counts.map((x) => {
          const dot = el("i");
          dot.style.background = String(x[2]);
          return el("div", {}, dot, el("span", { text: String(x[0]) }), el("b", { text: String(x[1]) }));
        }),
      ),
    ),
    el("div", { class: "ixs-raid-tips" }, el("p", { text: `⚠ ${h.stale} registros abiertos con más de 7 días sin actualizar.` }), el("p", { text: `◉ ${h.risks} riesgos y ${h.issues} problemas por atender.` }), el("p", { text: `✦ ${h.opportunities} oportunidades disponibles para seguimiento.` }), ...(h.documented ? [el("p", { text: `▦ ${h.documented} registros con probabilidad e impacto documentados.` })] : [])),
  );
}

/** @param {HTMLElement} root @param {any[]} all @param {any[]} rows @param {{detail: (id: number) => void}} h */
export function paintTable(root, all, rows, h) {
  $(root, "ixs-raid-count").textContent = `${rows.length} de ${all.length} registros`;
  const head = ["#", "Tipo", "Título", "Asignado", "Estado", "Severidad", "Prob.", "Iteración / etapa", "Últ. actualización", ""];
  $(root, "ixs-raid-tabla").replaceChildren(
    rows.length
      ? el(
          "div",
          { class: "ixs-raid-table-scroll" },
          el(
            "table",
            { class: "ixs-raid-table" },
            el("thead", {}, el("tr", {}, ...head.map((text) => el("th", { text })))),
            el(
              "tbody",
              {},
              ...rows.map((x) =>
                el(
                  "tr",
                  {},
                  el("td", {}, azureLink(x)),
                  el("td", {}, typeBadge(x)),
                  el("td", { class: "title", text: x.titulo == null ? "" : String(x.titulo) }),
                  el("td", { text: x.asignadoA == null ? "" : String(x.asignadoA) }),
                  el("td", {}, statusBadge(x)),
                  el("td", { text: String(x.severidad || "—") }),
                  el("td", { text: String(x.probabilidad || "—") }),
                  el("td", { text: iteration(x.iterationPath) || "—" }),
                  el("td", { text: dateText(x.ultimaActualizacion) }),
                  el("td", {}, el("button", { type: "button", class: "ixs-btn", text: "Ver detalle →", onclick: () => h.detail(Number(x.id)) })),
                ),
              ),
            ),
          ),
        )
      : empty("Sin registros para estos filtros."),
  );
}

/** @param {HTMLElement} root @param {any[]} rows */
export function paintMatrix(root, rows) {
  const m = matrix(rows);
  const box = $(root, "ixs-raid-matrix");
  if (!m.valid) {
    box.replaceChildren(empty("Probabilidad e impacto no están disponibles con los campos actuales de Azure. Se mostrarán al completar esos campos reales en los registros."));
    return;
  }
  box.replaceChildren(
    el("div", { class: "ixs-raid-matrix-head" }, el("span"), ...["Bajo", "Medio", "Alto"].map((text) => el("span", { text }))),
    ...["Alto", "Medio", "Bajo"].map((pr) =>
      el(
        "div",
        { class: "ixs-raid-matrix-row" },
        el("b", { text: pr }),
        ...["Bajo", "Medio", "Alto"].map((im) => el("div", { class: `ixs-raid-matrix-cell ${im === "Alto" && pr === "Alto" ? "red" : im === "Bajo" && pr === "Bajo" ? "green" : "yellow"}`, text: String(m.cell(im, pr) || "") })),
      ),
    ),
    el("small", { class: "ixs-raid-muted", text: `${m.valid} de ${m.open} abiertos tienen ambos campos registrados.` }),
  );
}

/** @param {HTMLElement} root @param {any[]} rows */
export function paintStages(root, rows) {
  const list = stages(rows);
  $(root, "ixs-raid-etapas").replaceChildren(
    list.length
      ? el(
          "div",
          { class: "ixs-raid-mini-table" },
          el("div", { class: "ixs-raid-mini-row head" }, ...["Etapa / iteración", "Riesgos", "Issues", "Oport.", "Total"].map((text) => el("b", { text }))),
          ...list.map((x) => el("div", { class: "ixs-raid-mini-row" }, el("span", { text: x.stage }), el("b", { text: String(x.Risk) }), el("b", { text: String(x.Issue) }), el("b", { text: String(x.Opportunity) }), el("b", { text: String(x.total) }))),
        )
      : empty("No hay registros abiertos por iteración."),
  );
}

/** @param {HTMLElement} root @param {any[]} rows */
export function paintPeople(root, rows) {
  const { list, max } = people(rows);
  $(root, "ixs-raid-personas").replaceChildren(
    list.length
      ? el(
          "div",
          { class: "ixs-raid-person-list" },
          ...list.map((x) => {
            const bar = el("em");
            bar.style.width = `${(100 * x[1]) / max}%`;
            return el("div", {}, el("span", { title: x[0], text: x[0] }), el("i", {}, bar), el("b", { text: String(x[1]) }));
          }),
        )
      : empty("Sin asignaciones abiertas."),
  );
}

/** Opciones de los filtros conservando lo elegido. @param {HTMLElement} root @param {string} id @param {string[]} values @param {string} placeholder */
export function paintOptions(root, id, values, placeholder) {
  const select = /** @type {HTMLSelectElement} */ ($(root, id));
  const current = select.value;
  select.replaceChildren(el("option", { value: "", text: placeholder }), ...values.map((value) => el("option", { value, text: value })));
  if (values.includes(current)) select.value = current;
}

/** @param {HTMLElement} root @param {string} text @param {boolean} visible */
export function paintNotice(root, text, warning) {
  $(root, "ixs-raid-notice").textContent = text;
  const warn = $(root, "ixs-raid-sync-warning");
  warn.hidden = !warning;
  warn.textContent = warning ? text : "";
}

/** Panel lateral con el detalle de un registro. @param {any} x @param {() => void} close */
export function detailDrawer(x, close) {
  const overlay = el("div", { id: "ixs-raid-detail-overlay", class: "ixs-raid-overlay", onclick: (/** @type {Event} */ e) => e.target === overlay && close() });
  const closeButton = (/** @type {string} */ label) => el("button", { type: "button", class: "ixs-btn", "aria-label": label || null, text: "✕", onclick: close });
  const open = el("a", { class: "ixs-btn primary ixs-raid-open-link", href: safeLink(x.url), target: "_blank", rel: "noopener noreferrer", text: "Abrir en Azure DevOps ↗" });
  const related = x.relacionados && x.relacionados.length ? x.relacionados : null;
  const relatedNodes = () => (related ? [el("div", { class: "ixs-raid-related" }, ...related.map((/** @type {any} */ r) => el("span", { text: `#${r.id || "Relacionado"}` })))] : []);
  const d = detail(x);
  if (d) {
    const card = (/** @type {any} */ c) => (c.text ? el("section", { class: "ixs-raid-risk-card" }, el("h4", {}, el("span", { text: c.icon }), c.title), el("p", { text: c.text })) : null);
    const pairs = (/** @type {any[]} */ list) => list.filter((p) => p.text).map((p) => el("div", { class: "ixs-raid-risk-pair" }, el("small", { text: p.label }), el("strong", { text: p.text })));
    const block = (/** @type {string} */ ico, /** @type {string} */ title, /** @type {any[]} */ items) => (items.length ? el("section", { class: "ixs-raid-risk-card" }, el("h4", {}, el("span", { text: ico }), title), ...items) : null);
    const strip = (/** @type {string} */ label, /** @type {string} */ value) => el("div", {}, el("small", { text: label }), el("strong", { text: value }));
    overlay.append(
      el(
        "aside",
        { class: "ixs-raid-drawer ixs-raid-risk-drawer", role: "dialog", "aria-modal": "true", "aria-label": d.aria },
        el("header", {}, el("b", { text: `${d.kind} #${x.id} · ${x.asignadoA || "Sin asignar"}` }), closeButton("Cerrar")),
        el("h3", { text: x.titulo == null ? "" : String(x.titulo) }),
        el("div", { class: "ixs-raid-risk-strip" }, strip("Estado", x.estado || "—"), strip("Área", x.areaPath || "—"), strip("Iteración", x.iterationPath || "—"), strip("Última actualización", dateText(x.ultimaActualizacion))),
        el(
          "div",
          { class: "ixs-raid-risk-layout" },
          el("div", { class: "ixs-raid-risk-column" }, ...d.left.map(card).filter(Boolean)),
          el(
            "div",
            { class: "ixs-raid-risk-column" },
            ...[block("▦", d.planningTitle, pairs(d.planning)), block("▥", d.secondaryTitle, pairs(d.secondary)), related ? el("section", { class: "ixs-raid-risk-card" }, el("h4", {}, el("span", { text: "↗" }), "Work Items relacionados"), ...relatedNodes()) : null, open].filter(Boolean),
          ),
        ),
      ),
    );
  } else {
    const field = (/** @type {string} */ label, /** @type {Node | string} */ value) => [el("div", { text: label }), el("div", {}, value)];
    overlay.append(
      el(
        "aside",
        { class: "ixs-raid-drawer", role: "dialog", "aria-modal": "true", "aria-label": "Detalle del registro" },
        el("header", {}, el("b", { text: "Detalle del registro" }), closeButton("")),
        el("h3", { text: `#${x.id} · ${x.titulo == null ? "" : x.titulo}` }),
        el("div", { class: "ixs-raid-drawer-fields" }, ...field("Tipo", typeBadge(x)), ...field("Estado", statusBadge(x)), ...field("Severidad", x.severidad || "—"), ...field("Impacto", x.impacto || "—"), ...field("Probabilidad", x.probabilidad || "—"), ...field("Responsable", x.asignadoA == null ? "" : String(x.asignadoA)), ...field("Iteración", iteration(x.iterationPath) || "—"), ...field("Últ. actualización", dateText(x.ultimaActualizacion))),
        el("h4", { text: "Descripción" }),
        el("p", { text: x.descripcion || "Sin descripción registrada." }),
        ...(related ? [el("h4", { text: "Work Items relacionados" }), ...relatedNodes()] : []),
        open,
      ),
    );
  }
  return overlay;
}

export { level };
