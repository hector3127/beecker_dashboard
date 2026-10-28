// @ts-check
// Pestaña Cliente: pinta la ficha, los contactos, el gobierno y los vínculos con
// el DOM. Las acciones las decide el controlador.
import { el } from "#app/lib/dom.js";
import { channelIcon, initials, levelClass } from "./client_model.js";

/** @param {HTMLElement} node @param {Record<string, string>} css */
const styled = (node, css) => {
  Object.assign(node.style, css);
  return node;
};
const text = (/** @type {any} */ v) => (v == null ? "" : String(v));
const dash = (/** @type {any} */ v) => text(v || "—");

/** @param {any} v */
const check = (v) => el("span", { class: `aer-client-check ${v ? "yes" : "no"}`, text: v ? "✓" : "" });
/** @param {any} level */
const pill = (level) => el("span", { class: `aer-pill ${levelClass(level)}`, text: dash(level) });

/** @param {string} title @param {string} hint @param {string} icon */
const heading = (title, hint, icon) => el("div", { class: "aer-client-section-heading" }, el("span", { class: "ico", text: icon }), el("div", {}, el("h3", { text: title }), el("div", { class: "hint", text: hint })));
/** @param {any[]} head @param {any[]} rows @param {string} empty @param {string} [cls] */
function table(head, rows, empty, cls = "aer-vivid-table") {
  return el("table", { class: cls }, el("thead", {}, el("tr", {}, ...head.map((t) => el("th", { text: t })))), el("tbody", {}, ...(rows.length ? rows : [el("tr", {}, el("td", { colspan: head.length, text: empty }))])));
}
/** @param {string} cls @param {string} title @param {string[]} items @param {string} none */
const box = (cls, title, items, none) => el("div", { class: `aer-client-box ${cls}` }, el("b", { text: title }), el("ul", { class: "aer-client-bullets" }, ...(items.length ? items : [none]).map((t) => el("li", { text: t }))));

/**
 * @param {HTMLElement} target @param {ReturnType<typeof import("./client_model.js").clientModel>} m
 * @param {{filters: any, showFilters: boolean}} view
 * @param {Record<string, any>} h
 */
export function renderClient(target, m, view, h) {
  const focused = !!document.activeElement && document.activeElement.id === "aer-client-search";
  const stake = (/** @type {any} */ x) => {
    const topics = String(x.alcance || "").split(/[,;|]/).map((v) => v.trim()).filter(Boolean).slice(0, 4);
    const chip = (/** @type {string} */ t) => styled(el("span", { class: "aer-client-role", text: t }), { background: "#f4f1fb", color: "#5e577b" });
    return el(
      "div",
      { class: "aer-client-stake" },
      el("span", { class: "aer-client-avatar", text: initials(x.nombre) }),
      el(
        "div",
        { class: "aer-client-info" },
        el("div", { class: "aer-client-name-line" }, el("b", { text: text(x.nombre) }), ...(x.rol ? [el("span", { class: "aer-client-role", text: text(x.rol) })] : [])),
        el("div", { class: "aer-client-jobline", text: `${text(x.cargo || "Sin cargo")} · ${text(m.clientName)}` }),
        el("div", { class: "aer-client-contactline" }, ...(x.correo ? [el("span", { class: "aer-client-mail", text: `✉ ${text(x.correo)}` })] : []), ...(x.telefono ? [el("span", { class: "aer-client-phone", text: `☎ ${text(x.telefono)}` })] : [])),
        el("div", { class: "aer-client-rowmeta" }, el("span", {}, el("span", { class: "label", text: "▥ Nivel de decisión:" }), " ", pill(x.nivelDecision))),
      ),
      el("button", { type: "button", class: "aer-btn", text: "Ver ficha ›", onclick: () => h.contact(x.uid) }),
      el("div", { class: "aer-client-topicline" }, el("strong", { text: "◉ Principales temas" }), ...(topics.length ? topics.map(chip) : [chip("Sin temas registrados")])),
    );
  };
  const kpi = (/** @type {any[]} */ k) => el("div", { class: "aer-vivid-card soft aer-client-kpi" }, el("div", { class: "aer-vivid-kpi-head" }, el("span", { class: `aer-vivid-icon ${k[4]}`, text: k[0] }), el("div", {}, el("div", { class: "aer-vivid-label", text: k[1] }), el("div", { class: "aer-vivid-value", text: String(k[2]) }), el("div", { class: "aer-vivid-sub", text: text(k[3]) }))));
  const linkOf = (/** @type {any} */ x) => () => h.openLink(x.url);

  const search = el("input", { id: "aer-client-search", type: "search", placeholder: "Buscar contacto, correo o rol...", oninput: (/** @type {Event} */ e) => h.search(/** @type {HTMLInputElement} */ (e.target).value) });
  /** @type {HTMLInputElement} */ (search).value = view.filters.q;
  const select = (/** @type {string} */ key, /** @type {string} */ first, /** @type {string[]} */ options) => {
    const node = el("select", { onchange: (/** @type {Event} */ e) => h.filter(key, /** @type {HTMLSelectElement} */ (e.target).value) }, el("option", { value: "", text: first }), ...options.map((v) => el("option", { value: v, text: v })));
    /** @type {HTMLSelectElement} */ (node).value = view.filters[key];
    return node;
  };

  const filterBar = el("div", { class: "aer-client-filterbar" }, select("rol", "Todos los roles", m.roles), select("area", "Todas las áreas", m.areas), select("decision", "Nivel decisión", ["Alto", "Medio", "Bajo"]), select("estado", "Todos los estados", ["Activo", "Inactivo"]), el("div", { class: "clear" }, el("button", { type: "button", class: "aer-btn", text: "Limpiar filtros", onclick: h.clearFilters })));
  // El primer elemento del select de nivel y estado no lleva "value" en el texto anterior: se conserva.
  const directoryRow = (/** @type {any} */ x) => {
    const dot = styled(el("span", { text: "●" }), { color: String(x.estado).toLowerCase() === "inactivo" ? "#c83c4d" : "#1ea161", fontWeight: "800" });
    return el("tr", {}, el("td", { text: text(x.nombre) }), el("td", { text: dash(x.cargo) }), el("td", { text: dash(x.rol) }), el("td", { text: dash(x.area) }), el("td", { text: dash(x.correo) }), el("td", { class: "phone", text: dash(x.telefono) }), el("td", {}, pill(x.nivelDecision)), el("td", {}, dot, ` ${text(x.estado || "Activo")}`), el("td", {}, el("button", { type: "button", class: "aer-btn", text: "✎", onclick: () => h.contact(x.uid) })));
  };

  const matrixRow = (/** @type {any} */ x) => el("tr", {}, el("td", { text: text(x.nombre) }), el("td", {}, check(x.requerimientos)), el("td", {}, check(x.aprueba)), el("td", {}, check(x.valida)), el("td", {}, check(x.decide)), el("td", {}, check(x.informado)));
  const docRow = (/** @type {any} */ x) => {
    const open = (/** @type {Event} */ e) => {
      e.preventDefault();
      h.openLink(x.url);
    };
    return el(
      "tr",
      {},
      el("td", { text: text(x.nombre) }),
      el("td", { text: dash(x.tipo) }),
      el("td", {}, el("a", { class: "aer-client-doc-link", href: "#", onclick: open, text: "🔗 Ver vínculo" })),
      el("td", {}, el("div", { class: "aer-client-doc-actions" }, el("button", { type: "button", class: "aer-btn", text: text(x.accion || "Abrir"), onclick: linkOf(x) }), el("button", { type: "button", class: "aer-btn", text: "⋮", onclick: () => h.document(x.uid) }))),
    );
  };

  const note = styled(el("div", { class: "aer-client-note" }, el("b", { text: "ⓘ" }), el("span", { text: "Canales principales de comunicación con el cliente." })), { margin: "0", padding: "0", border: "0" });
  const matrixNote = el("div", { class: "aer-client-note" }, check(true), el("span", {}, el("b", { text: "Sí / Participa" })), check(false), el("span", { text: "No aplica" }));
  const scope = styled(el("div", { class: "aer-client-scope" }, box("blue", "ⓘ Temas principales", m.topics, "Sin temas registrados"), box("green", "✓ Roles representados", m.activeRoles, "Sin roles definidos")), { marginTop: "10px" });
  const logo = el("span", { class: "aer-client-badge-logo", text: text(m.clientName).slice(0, 4).toUpperCase() });
  const factRow = (/** @type {any[]} */ r) => el("tr", {}, el("th", {}, styled(el("span", { text: r[0] }), { display: "inline-block", width: "18px" }), r[1]), el("td", { text: text(r[2]) }));
  const iconButtonRow = styled(el("div", {}, el("button", { type: "button", class: "aer-btn primary", text: "＋ Agregar link", onclick: () => h.document() })), { display: "flex", gap: "8px", flexWrap: "wrap" });

  target.replaceChildren(
    el(
      "div",
      { class: "aer-client-shell" },
      el(
        "div",
        { class: "aer-vivid-card aer-client-hero" },
        el(
          "div",
          { class: "aer-action-hero" },
          el("div", { class: "aer-client-title" }, el("span", { class: "aer-client-title-icon", text: "👥" }), el("div", {}, el("h3", { text: "Cliente & stakeholders" }), el("div", { class: "sub", text: "Consulta de contactos, roles y alcance de participación del cliente." }))),
          el("div", { class: "aer-client-actions" }, el("button", { type: "button", class: "aer-btn primary", text: "＋ Agregar contacto", onclick: () => h.contact() }), el("button", { type: "button", class: "aer-btn", text: "✎ Editar información", onclick: h.info }), el("button", { type: "button", class: "aer-btn", text: "⇩ Exportar", onclick: h.exportContacts })),
        ),
        el("div", { class: "aer-client-kpis" }, ...m.kpis.map(kpi)),
      ),
      el(
        "div",
        { class: "aer-client-main" },
        el(
          "div",
          { class: "aer-vivid-card aer-client-card" },
          el("div", { class: "aer-section-title" }, heading("Stakeholders clave", "Personas clave del cliente y su participación en el proyecto.", "👥")),
          el("div", { class: "aer-client-stake-list" }, ...(m.key.length ? m.key.map(stake) : [el("div", { class: "aer-client-empty", text: "Aún no hay contactos registrados. Usa “Agregar contacto”." })])),
          el(
            "div",
            { class: "aer-client-inline-block" },
            el("div", { class: "aer-section-title" }, heading("Matriz de participación", "Nivel de participación de cada stakeholder en el proyecto.", "▦")),
            table(["Stakeholder", "Requerimientos", "Aprueba", "Valida", "Decide", "Informado"], m.active.slice(0, 8).map(matrixRow), "Sin contactos.", "aer-vivid-table aer-client-matrix"),
            matrixNote,
            scope,
          ),
        ),
        el(
          "div",
          { class: "aer-client-stack" },
          el(
            "div",
            { class: "aer-vivid-card aer-client-card" },
            el("div", { class: "aer-client-profile-head" }, heading("Ficha del cliente", "Información general del cliente y esquema de relación.", "▦"), el("div", { class: "aer-client-badge" }, logo, el("span", {}, el("b", { text: text(m.clientName) }), el("small", { text: "Cliente" })))),
            el("table", { class: "aer-client-side-table" }, el("tbody", {}, ...m.facts.map(factRow))),
            el("div", { class: "aer-client-mode-wrap" }, el("div", {}, el("div", { class: "aer-client-mode-title", text: "Modalidad de comunicación" }), el("div", { class: "aer-client-mode" }, ...(m.channels.length ? m.channels.map((c) => el("span", { text: `${channelIcon(c)} ${c}` })) : [el("span", { text: "● Sin canales" })]))), note),
          ),
          el(
            "div",
            { class: "aer-vivid-card aer-client-card aer-client-government" },
            el("div", { class: "aer-section-title" }, heading("Gobierno y comunicación", "Reuniones y canales de coordinación con el cliente.", "👥"), el("button", { type: "button", class: "aer-btn", text: "✎ Editar", onclick: h.governance })),
            table(["Reunión", "Frecuencia", "Participantes", "Canal"], m.governance.map((r) => el("tr", {}, el("td", { text: text(r.reunion) }), el("td", { text: text(r.frecuencia) }), el("td", { text: text(r.participantes) }), el("td", {}, el("span", { class: "aer-client-channel", text: `${channelIcon(text(r.canal))} ${text(r.canal)}` })))), "Sin reuniones configuradas."),
          ),
          el(
            "div",
            { class: "aer-vivid-card aer-client-card aer-client-docs" },
            el("div", { class: "aer-section-title" }, heading("Documentación y links", "Documentos de referencia, plantillas y recursos del proyecto.", "📄"), iconButtonRow),
            styled(el("div", {}, table(["Nombre", "Tipo", "URL / vínculo", "Acción"], m.docs.map(docRow), "Sin documentación registrada.", "aer-vivid-table aer-client-docs-table")), { overflow: "auto" }),
            el("div", { class: "aer-client-quicklinks" }, ...m.quickDocs.map((x) => el("div", { class: "aer-client-quicklink" }, el("b", { text: `${x[0]} ${x[1]}` }), el("span", { text: `${x[2]} ${x[3]}` })))),
          ),
        ),
      ),
      el("div", { class: "aer-client-bottom single" }, el("div", { class: "aer-vivid-card aer-client-card" }, el("div", { class: "aer-section-title" }, heading("Alcance de participación", "Áreas incluidas en el alcance de participación del cliente.", "◔")), el("div", { class: "aer-client-scope" }, box("green", "✓ Incluido", m.included, "Sin áreas definidas"), box("blue", "ⓘ Referencias / informado", m.informed, "Sin referencias")), el("div", { class: "aer-client-note" }, el("b", { text: "ⓘ" }), " Esta vista muestra información persistida de contactos, roles y alcance de participación."))),
      el(
        "div",
        { class: "aer-vivid-card aer-client-card" },
        el(
          "div",
          { class: "aer-section-title" },
          heading("Directorio de contactos", `${m.filtered.length} de ${m.all.length} contacto(s)`, "▣"),
          el("div", { class: "aer-client-directory-tools" }, search, el("button", { type: "button", class: `aer-btn ${view.showFilters ? "primary" : ""}`.trim(), text: "⌄ Filtros", onclick: h.toggleFilters })),
        ),
        ...(view.showFilters ? [filterBar] : []),
        styled(el("div", {}, table(["Persona", "Cargo", "Rol en proyecto", "Área", "Correo", "Teléfono", "Nivel decisión", "Estado", "Editar"], m.filtered.map(directoryRow), "No hay contactos que coincidan con los filtros.", "aer-vivid-table aer-client-directory")), { overflow: "auto" }),
      ),
    ),
  );
  if (focused) {
    const node = /** @type {HTMLInputElement} */ (target.querySelector("#aer-client-search"));
    node.focus();
    node.setSelectionRange(node.value.length, node.value.length);
  }
}

/** Aviso temporal, igual al anterior. @param {string} message @param {string} [type] */
export function toast(message, type = "success") {
  const node = el("div", { class: `aer-toast ${type}`, text: message });
  document.body.append(node);
  requestAnimationFrame(() => node.classList.add("show"));
  setTimeout(() => {
    node.classList.remove("show");
    setTimeout(() => node.remove(), 220);
  }, 1800);
}

/** Ventana de la pestaña; los hijos de `content` van directo en `.aer-modal`. @param {HTMLElement} content @param {() => void} close */
export function modal(content, close) {
  const back = el("div", { class: "aer-modal-back", id: "aer-modal-back", onclick: (/** @type {Event} */ e) => e.target === back && close() }, el("div", { class: "aer-modal" }, ...content.childNodes));
  return back;
}

const closeButton = (/** @type {() => void} */ close) => el("button", { type: "button", class: "aer-btn", text: "✕", onclick: close });
/** @param {string} title @param {() => void} close @param {string} [subtitle] */
function head(title, close, subtitle = "") {
  if (!subtitle) return styled(el("div", {}, el("h3", { text: title }), closeButton(close)), { display: "flex", justifyContent: "space-between", alignItems: "center" });
  const h3 = styled(el("h3", { text: title }), { margin: "0" });
  return styled(el("div", {}, el("div", {}, h3, el("div", { class: "aer-sub", text: subtitle })), closeButton(close)), { display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" });
}
/** @param {string} id @param {any} value @param {Record<string, any>} [extra] */
function input(id, value, extra = {}) {
  const node = el("input", { id, ...extra });
  /** @type {HTMLInputElement} */ (node).value = text(value);
  return node;
}
const field = (/** @type {string} */ label, /** @type {HTMLElement} */ control, cls = "") => el("label", cls ? { class: cls } : {}, label, control);
const area = (/** @type {string} */ id, /** @type {any} */ value) => el("textarea", { id }, text(value));
const selectOf = (/** @type {string} */ id, /** @type {string[]} */ options, /** @type {(v: string) => boolean} */ chosen) => el("select", { id }, ...options.map((v) => el("option", { text: v, selected: chosen(v) ? true : null })));

/** Formulario de contacto. @param {any} x @param {string} uid @param {{close: () => void, save: () => void, remove: (uid: string) => void}} h */
export function contactModal(x, uid, h) {
  const checks = [["acc-req", "Requerimientos", x.requerimientos], ["acc-apr", "Aprueba", x.aprueba], ["acc-val", "Valida", x.valida], ["acc-dec", "Decide", x.decide], ["acc-inf", "Informado", x.informado], ["acc-decidor", "Es decisor", x.esDecisor]];
  const actions = styled(el("div", { class: "aer-actions" }, ...(uid ? [el("button", { type: "button", class: "aer-btn danger", text: "Eliminar", onclick: () => h.remove(uid) })] : []), el("button", { type: "button", class: "aer-btn primary", text: "Guardar contacto", onclick: h.save })), { marginTop: "12px" });
  return modal(
    el(
      "div",
      {},
      head(`${uid ? "Editar" : "Agregar"} contacto`, h.close),
      el(
        "div",
        { class: "aer-formgrid" },
        field("Nombre", input("acc-nom", x.nombre || "")),
        field("Cargo", input("acc-cargo", x.cargo || "")),
        field("Rol en el proyecto", input("acc-rol", x.rol || "")),
        field("Área", input("acc-area", x.area || "")),
        field("Correo", input("acc-mail", x.correo || "", { type: "email" })),
        field("Teléfono", input("acc-tel", x.telefono || "")),
        field("Nivel de decisión", selectOf("acc-nivel", ["Alto", "Medio", "Bajo"], (v) => x.nivelDecision === v)),
        field("Estado", selectOf("acc-est", ["Activo", "Inactivo"], (v) => String(x.estado || "Activo").toLowerCase() === v.toLowerCase())),
        field("Canal principal", input("acc-canal", x.canal || "", { placeholder: "Teams, Correo..." })),
        field("Alcance / responsabilidades", area("acc-alc", x.alcance || ""), "aer-span2"),
        el("label", { class: "aer-span2" }, "Participación", el("div", { class: "aer-client-checkgrid" }, ...checks.map((c) => el("label", {}, el("input", { type: "checkbox", id: c[0], checked: c[2] ? true : null }), ` ${c[1]}`)))),
        field("Notas", area("acc-notas", x.notas || ""), "aer-span2"),
      ),
      actions,
    ),
    h.close,
  );
}

/** Ficha del cliente. @param {any} x @param {{close: () => void, save: () => void}} h */
export function infoModal(x, h) {
  const actions = styled(el("div", { class: "aer-actions" }, el("button", { type: "button", class: "aer-btn primary", text: "Guardar información", onclick: h.save })), { marginTop: "12px" });
  return modal(
    el(
      "div",
      {},
      head("Editar información del cliente", h.close),
      el("div", { class: "aer-formgrid" }, field("Área principal", input("aci-area", x.areaPrincipal || "")), field("Sponsor", input("aci-sponsor", x.sponsor || "")), field("Product Owner", input("aci-po", x.productOwner || "")), field("Correo de distribución", input("aci-mail", x.correoDistribucion || "", { type: "email" })), field("Ruta de escalamiento", input("aci-ruta", x.rutaEscalamiento || ""), "aer-span2"), field("Canales", input("aci-canales", x.canales || "", { placeholder: "Teams, Correo, Comité operativo" }), "aer-span2")),
      actions,
    ),
    h.close,
  );
}

/** @param {any} x */
function governanceRow(x = {}) {
  const cell = (/** @type {string} */ key, /** @type {string} */ placeholder) => {
    const node = el("input", { "data-gov": key, placeholder });
    /** @type {HTMLInputElement} */ (node).value = text(x[key] || "");
    return node;
  };
  const row = el("div", { class: "aer-gov-edit-row" }, cell("reunion", "Reunión"), cell("frecuencia", "Frecuencia"), cell("participantes", "Participantes"), cell("canal", "Canal"), el("button", { type: "button", class: "del", title: "Quitar fila", text: "✕", onclick: () => row.remove() }));
  return row;
}

/** Editor de gobierno y comunicación. @param {any[]} rows @param {{close: () => void, save: () => void}} h */
export function governanceModal(rows, h) {
  const editor = el("div", { id: "aer-gov-editor", class: "aer-gov-editor" }, ...rows.map(governanceRow));
  const labels = styled(el("div", { class: "aer-gov-head" }, ...["Reunión", "Frecuencia", "Participantes", "Canal"].map((t) => el("span", { text: t })), el("span")), { marginTop: "14px" });
  return modal(
    el(
      "div",
      {},
      head("Editar gobierno y comunicación", h.close, "Edita directamente las reuniones, frecuencia, participantes y canal."),
      labels,
      editor,
      el("div", { class: "aer-gov-actions" }, el("button", { type: "button", class: "aer-btn", text: "＋ Agregar reunión", onclick: () => editor.append(governanceRow()) }), el("button", { type: "button", class: "aer-btn primary", text: "Guardar cambios", onclick: h.save })),
    ),
    h.close,
  );
}

/** Documento o vínculo. @param {any} x @param {string} uid @param {{close: () => void, save: () => void, remove: (uid: string) => void}} h */
export function documentModal(x, uid, h) {
  const kind = String(x.tipo || "");
  const types = [["Carpeta", (/** @type {string} */ k) => k === "Carpeta" || k === "Procedimiento" || k === ""], ["Plantilla", (/** @type {string} */ k) => k === "Plantilla"], ["Repositorio", (/** @type {string} */ k) => k === "Repositorio"], ["Referencia", (/** @type {string} */ k) => k === "Referencia"], ["Documento", (/** @type {string} */ k) => k === "Documento"]];
  types.push(["Plan de trabajo", (/** @type {string} */ k) => k === "Plan de trabajo"], ["Roadmap", (/** @type {string} */ k) => k === "Roadmap"]);
  const select = el("select", { id: "acd-tipo" }, ...types.map((t) => el("option", { text: String(t[0]), selected: /** @type {Function} */ (t[1])(kind) ? true : null })));
  const grid = styled(el("div", { class: "aer-formgrid" }, field("Nombre", input("acd-nom", x.nombre || "")), field("Tipo", select), field("URL / vínculo", input("acd-url", x.url || "", { placeholder: "https://..." }), "aer-span2"), field("Texto del botón", input("acd-accion", x.accion || "Abrir")), field("Notas", input("acd-notas", x.notas || ""))), { marginTop: "12px" });
  const actions = styled(el("div", { class: "aer-actions" }, ...(uid ? [el("button", { type: "button", class: "aer-btn", text: "Eliminar", onclick: () => h.remove(uid) })] : []), el("button", { type: "button", class: "aer-btn primary", text: "Guardar link", onclick: h.save })), { marginTop: "12px" });
  return modal(el("div", {}, head(`${uid ? "Editar" : "Agregar"} documentación / link`, h.close, "Registra documentos, plantillas, repositorios o referencias del proyecto."), grid, actions), h.close);
}
