// @ts-check
// Ventana de comunicados: pinta el formulario, la vista previa y el hilo de
// Gmail. No decide nada: entrega lo escrito al controlador.
import { el } from "#app/lib/dom.js";
import { KINDS, STAGES, fmtDate, previewSubject } from "./communique_model.js";

const ICONS = {
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>',
  clip: '<path d="m21 11-8.6 8.6a5 5 0 0 1-7-7L14 4a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4l8-8"/>',
  link: '<path d="M10 13a5 5 0 0 0 7 .3l3-3a5 5 0 0 0-7-7l-2 2M14 11a5 5 0 0 0-7-.3l-3 3a5 5 0 0 0 7 7l2-2"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  upload: '<path d="M7 18a4.5 4.5 0 0 1-.6-8.96A6 6 0 0 1 18 8.5a4 4 0 0 1-.5 9.5"/><path d="M12 12v8M9 15l3-3 3 3"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  spark: '<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3zM19 16l.7 1.8L21.5 18.5l-1.8.7L19 21l-.7-1.8-1.8-.7 1.8-.7z"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  send: '<path d="m22 2-11 11M22 2l-7 20-4-9-9-4z"/>',
  check: '<path d="M4 12l5 5L20 6"/>',
};

/** Fragmento SVG fijo (constantes de este archivo, nunca datos). @param {string} inner @param {string} viewBox @param {string} attrs */
function svgNode(inner, viewBox, attrs) {
  const doc = new DOMParser().parseFromString(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" ${attrs} aria-hidden="true">${inner}</svg>`, "image/svg+xml");
  return document.importNode(doc.documentElement, true);
}
/** @param {keyof typeof ICONS} name @param {string} [cls] */
export const icon = (name, cls = "") => {
  const node = svgNode(ICONS[name], "0 0 24 24", 'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"');
  node.setAttribute("class", `ixe-svg ${cls}`.trim());
  return node;
};

const BADGE = { pdf: "#e5484d", png: "#6e56cf", jpg: "#6e56cf", jpeg: "#6e56cf", xlsx: "#1f9d55", docx: "#2b6cd6" };
/** @param {number} bytes */
export const sizeText = (bytes) => (bytes >= 1048576 ? (bytes / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(bytes / 1024)) + " KB");
/** @param {string} name */
function fileBadge(name) {
  const ext = (name.split(".").pop() || "").toLowerCase();
  const badge = el("span", { class: "badge", text: ext });
  badge.style.background = /** @type {any} */ (BADGE)[ext] || "#7a7f9a";
  return badge;
}
/** @param {File} f @param {(() => void) | null} [remove] */
function fileRow(f, remove = null) {
  return el("div", { class: "ixe-file" }, fileBadge(f.name), el("span", { class: "name", text: f.name }), el("span", { class: "size", text: sizeText(f.size) }), ...(remove ? [el("button", { type: "button", "aria-label": "Quitar archivo", onclick: remove }, icon("trash"))] : []));
}

/** @param {any} field @param {string} value */
function fieldNode(field, value) {
  const star = field.required ? [" ", el("em", { text: "*" })] : [];
  /** @type {HTMLElement} */
  let control;
  if (field.type === "stage") {
    control = el("select", { "data-key": field.key }, el("option", { value: "", text: "Selecciona…" }), ...STAGES.map((s) => el("option", { value: s, text: s })));
    /** @type {HTMLSelectElement} */ (control).value = value;
  } else if (field.type === "textarea") {
    control = el("textarea", { "data-key": field.key, maxlength: field.max, placeholder: field.placeholder || "" });
    /** @type {HTMLTextAreaElement} */ (control).value = value;
  } else {
    control = el("input", { "data-key": field.key, type: field.type === "date" ? "date" : "text", placeholder: field.placeholder || "", maxlength: field.max || null, autocomplete: "off" });
    /** @type {HTMLInputElement} */ (control).value = value;
  }
  const wrap = el("span", { class: field.type === "textarea" ? "ixe-input area" : "ixe-input" }, ...(field.type === "date" ? [icon("calendar")] : []), control);
  const label = el("label", { class: "ixe-field" }, field.label, ...star, wrap);
  if (field.type !== "textarea") return field.full ? el("div", { class: "full" }, label) : label;
  const count = el("span", { "data-count": field.key, text: String(value.length) });
  return el("div", { class: "full" }, label, el("div", { class: "ixe-count" }, count, `/${field.max}`));
}

/** @param {any[]} segments @param {(n: string) => HTMLElement|null} unused */
function segmentNodes(segments) {
  return segments.flatMap((/** @type {any} */ s) => {
    if (typeof s === "string") return [s];
    if (s.b !== undefined) return [el("b", { text: s.b })];
    if (s.ph !== undefined) return [el("span", { class: "ph", text: s.ph })];
    if (s.a !== undefined) return [el("a", { href: s.a, target: "_blank", rel: "noopener noreferrer", text: s.a })];
    return [];
  });
}

/** Pinta los bloques de la vista previa. @param {HTMLElement} target @param {any[][]} blocks */
export function paintPreview(target, blocks) {
  const nodes = blocks.map((block) => {
    if (block[0] && block[0].li) return el("ul", {}, ...block.map((/** @type {any} */ item) => el("li", {}, ...segmentNodes(item.li))));
    if (block[0] && block[0].road !== undefined) {
      const url = block[0].road;
      const inner = url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer", text: "Ver roadmap" }) : el("span", { class: "ph", text: "[link del roadmap]" });
      return el("div", { class: "ixe-roadmap" }, icon("clip"), el("span", {}, "Roadmap actualizado: ", inner));
    }
    return el("p", {}, ...segmentNodes(block));
  });
  target.replaceChildren(...nodes);
}

/**
 * @param {{family: string, kinds: string[], kind: string, project: string, values: Record<string, string>, handlers: Record<string, any>}} o
 */
export function createDialog(o) {
  const kindsRow = el("div", { class: "ixe-kinds", role: "tablist", "aria-label": "Tipo de comunicado" }, ...o.kinds.map((k) => el("button", { type: "button", role: "tab", class: "ixe-kind", "data-kind": k, text: KINDS[k].label, onclick: () => o.handlers.setKind(k) })));
  const title = el("h2");
  const subtitle = el("p");
  const sId = el("span", { class: "id", text: "—" });
  const sStage = el("span", {}, "—");
  const sDates = el("small", { text: "Sin capturar" });
  const sFiles = el("small", { text: "0 archivos" });
  const sRoad = el("small", { text: "Sin link" });
  const sRoadTitle = el("b", { text: "Roadmap" });
  const baseGrid = el("div", { class: "ixe-grid" });
  const idInput = el("input", { id: "ixe-id", placeholder: "Ej. MCC.015_S3", autocomplete: "off" });
  /** @type {HTMLInputElement} */ (idInput).value = o.project;
  const linkLabel = el("label", { class: "ixe-field", for: "ixe-link" });
  const linkOk = el("span", { class: "ixe-ok" }, icon("check"), "Se enviará por vínculo");
  linkOk.style.visibility = "hidden";
  const linkInput = el("input", { id: "ixe-link", type: "url", placeholder: "https://drive.google.com/...", autocomplete: "off" });
  const linkTitle = el("h3");
  const linkNote = el("div", { class: "ixe-note" });
  const filesTitle = el("h3");
  const fileInput = /** @type {HTMLInputElement} */ (el("input", { type: "file", id: "ixe-file", multiple: true, accept: ".pdf,.png,.jpg,.jpeg,.xlsx,.docx", hidden: true }));
  const drop = el("div", { class: "ixe-drop", id: "ixe-drop", tabindex: "0" }, icon("upload"), "Arrastra archivos aquí o haz clic para adjuntar", el("small", { text: "Formatos permitidos: PDF, PNG, JPG, XLSX, DOCX (máx. 10 MB por archivo)" }));
  const filesBox = el("div", { class: "ixe-files" });
  const subject = el("span", { class: "v" });
  const body = el("div");
  const attached = el("div", { class: "ixe-attached", hidden: true });
  const gmail = el("section", { class: "ixe-card", id: "ixe-gmail" });
  const toast = el("div", { class: "ixe-toast", id: "ixe-toast" });
  const sendLabel = el("span", { text: "Generar comunicado" });
  const send = el("button", { type: "button", class: "ixe-btn primary", id: "ixe-send", onclick: o.handlers.send }, icon("send"), sendLabel);
  const stageIcon = el("i");

  const dialog = el(
    "div",
    { class: "ixe-dialog", role: "dialog", "aria-modal": "true", "aria-label": "Comunicados de proyecto" },
    el("div", { class: "ixe-head" }, el("span", { class: "ixe-head-icon" }, icon("clock")), el("div", { class: "ixe-head-text" }, title, subtitle), kindsRow, el("button", { type: "button", class: "ixe-close", "aria-label": "Cerrar", text: "✕", onclick: o.handlers.close })),
    el(
      "div",
      { class: "ixe-summary" },
      el("div", { class: "ixe-chip main" }, el("span", { class: "ixe-ico" }, icon("file")), sId, el("span", { class: "stage" }, stageIcon, sStage)),
      el("div", { class: "ixe-chip" }, el("span", { class: "ixe-ico" }, icon("calendar")), el("span", {}, el("b", { text: "Fechas capturadas" }), sDates)),
      el("div", { class: "ixe-chip" }, el("span", { class: "ixe-ico" }, icon("clip")), el("span", {}, el("b", { text: "Archivos adjuntos" }), sFiles)),
      el("div", { class: "ixe-chip" }, el("span", { class: "ixe-ico" }, icon("link")), el("span", {}, sRoadTitle, sRoad)),
    ),
    el(
      "div",
      { class: "ixe-body" },
      el(
        "div",
        { class: "ixe-col" },
        el("section", { class: "ixe-card" }, el("div", { class: "ixe-card-head" }, el("span", { class: "ixe-num", text: "1" }), el("h3", { text: "Datos base" }), el("span", { class: "hint" }, icon("info"), "El resto del texto del comunicado se genera automáticamente.")), baseGrid),
        el(
          "section",
          { class: "ixe-card" },
          el("div", { class: "ixe-card-head" }, el("span", { class: "ixe-num", text: "2" }), linkTitle),
          el("div", { class: "ixe-label-row" }, linkLabel, linkOk),
          el("div", { class: "ixe-linkrow" }, el("span", { class: "ixe-input" }, icon("clip"), linkInput), el("button", { type: "button", class: "ixe-btn", onclick: o.handlers.openLink }, icon("external"), "Abrir link")),
          linkNote,
        ),
        el("section", { class: "ixe-card" }, el("div", { class: "ixe-card-head" }, el("span", { class: "ixe-num", text: "3" }), filesTitle, el("span", { class: "hint" }, icon("info"), "Puedes adjuntar evidencias, capturas o documentos de soporte.")), drop, fileInput, filesBox),
      ),
      el(
        "div",
        { class: "ixe-col" },
        el("section", { class: "ixe-card" }, el("div", { class: "ixe-prev-head" }, el("span", { class: "ixe-ico" }, icon("eye")), el("h3", { text: "Vista previa del comunicado" }), el("button", { type: "button", class: "ixe-btn small", onclick: () => o.handlers.soon("Editar plantilla") }, icon("edit"), "Editar plantilla")), el("div", { class: "ixe-preview" }, el("div", { class: "ixe-subject" }, el("span", { text: "Asunto:" }), subject), body, attached)),
        gmail,
      ),
    ),
    el("div", { class: "ixe-foot" }, el("button", { type: "button", class: "ixe-btn", onclick: o.handlers.clear }, icon("trash"), "Limpiar"), el("span", { class: "grow" }), el("button", { type: "button", class: "ixe-btn", onclick: () => o.handlers.soon("Sugerir redacción con IA") }, icon("spark"), "Sugerir redacción con IA"), el("span", { class: "sep" }), el("button", { type: "button", class: "ixe-btn", onclick: o.handlers.copy }, icon("copy"), "Copiar texto"), send),
    toast,
  );
  const overlay = el("div", { id: "ixe-overlay", class: "ixe-overlay" }, dialog);
  let down = false;
  overlay.addEventListener("mousedown", (e) => (down = e.target === overlay));
  overlay.addEventListener("click", (e) => e.target === overlay && down && o.handlers.close());
  drop.addEventListener("click", () => fileInput.click());
  drop.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });
  drop.addEventListener("dragover", (e) => {
    e.preventDefault();
    drop.classList.add("over");
  });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("over");
    o.handlers.addFiles(e.dataTransfer && e.dataTransfer.files);
  });
  fileInput.addEventListener("change", () => {
    o.handlers.addFiles(fileInput.files);
    fileInput.value = "";
  });
  overlay.addEventListener("input", o.handlers.changed);
  overlay.addEventListener("change", o.handlers.changed);

  return {
    overlay,
    /** Cambia los campos y textos al tipo elegido. @param {string} kind @param {Record<string, string>} values */
    setKind(kind, values) {
      const k = KINDS[kind];
      title.textContent = k.title;
      subtitle.textContent = k.subtitle;
      kindsRow.querySelectorAll(".ixe-kind").forEach((b) => {
        const on = /** @type {HTMLElement} */ (b).dataset.kind === kind;
        b.classList.toggle("on", on);
        b.setAttribute("aria-selected", String(on));
      });
      const idField = el("label", { class: "ixe-field" }, "Proyecto / ID ", el("em", { text: "*" }), el("span", { class: "ixe-input" }, icon("search"), idInput));
      baseGrid.replaceChildren(idField, ...k.fields.map((f) => fieldNode(f, values[f.key] || "")));
      linkLabel.replaceChildren(k.linkLabel, ...(k.linkRequired ? [" ", el("em", { text: "*" })] : []));
      linkTitle.textContent = k.linkTitle;
      linkNote.replaceChildren(icon("info"), k.linkNote);
      filesTitle.textContent = k.filesTitle;
      /** @type {HTMLInputElement} */ (linkInput).value = values.link || "";
      sRoadTitle.textContent = kind === "extension" ? "Roadmap" : k.linkTitle;
      stageIcon.hidden = !k.fields.some((f) => f.type === "stage");
      sendLabel.textContent = "Generar comunicado";
    },
    /** Datos escritos en el formulario. */
    read() {
      /** @type {Record<string, string>} */
      const values = {};
      baseGrid.querySelectorAll("[data-key]").forEach((n) => {
        values[/** @type {HTMLElement} */ (n).dataset.key || ""] = /** @type {HTMLInputElement} */ (n).value;
      });
      values.link = /** @type {HTMLInputElement} */ (linkInput).value;
      return { values, project: /** @type {HTMLInputElement} */ (idInput).value };
    },
    clearFields() {
      baseGrid.querySelectorAll("[data-key]").forEach((n) => {
        /** @type {HTMLInputElement} */ (n).value = "";
      });
      /** @type {HTMLInputElement} */ (linkInput).value = "";
    },
    /** @param {string} key @param {string} value */
    setField(key, value) {
      const node = /** @type {HTMLInputElement | null} */ (baseGrid.querySelector(`[data-key="${key}"]`));
      if (node) node.value = value;
    },
    /** Resumen, vista previa y archivos. @param {any} s */
    paint(s) {
      baseGrid.querySelectorAll("[data-count]").forEach((n) => {
        const key = /** @type {HTMLElement} */ (n).dataset.count || "";
        n.textContent = String((s.values[key] || "").length);
      });
      sId.textContent = s.project.trim() || "—";
      sStage.textContent = s.values.stage || (stageIcon.hidden ? s.kindLabel : "Sin etapa");
      sDates.textContent = s.dates || "Sin capturar";
      sFiles.textContent = s.files.length + (s.files.length === 1 ? " archivo" : " archivos");
      const hasLink = !!(s.values.link || "").trim();
      sRoad.textContent = hasLink ? "Con link" : "Sin link";
      linkOk.style.visibility = hasLink ? "visible" : "hidden";
      subject.textContent = previewSubject(s.thread);
      paintPreview(body, s.blocks);
      attached.hidden = !s.files.length;
      attached.replaceChildren(...(s.files.length ? ["Archivos adjuntos en el correo:", ...s.files.map((/** @type {File} */ f) => fileRow(f))] : []));
      filesBox.replaceChildren(...s.files.map((/** @type {File} */ f, /** @type {number} */ i) => fileRow(f, () => o.handlers.removeFile(i))));
    },
    gmail,
    /** @param {string} text */
    toast(text) {
      toast.textContent = text;
      toast.classList.add("show");
      clearTimeout(/** @type {any} */ (toast)._t);
      /** @type {any} */ (toast)._t = setTimeout(() => toast.classList.remove("show"), 3200);
    },
    previewText: () => body.innerText.trim(),
    /** Confirmación con el estilo de las ventanas del portal. @param {string} text @returns {Promise<boolean>} */
    confirm(text) {
      return new Promise((resolve) => {
        const finish = (/** @type {boolean} */ answer) => {
          document.removeEventListener("keydown", onEsc, true);
          back.remove();
          resolve(answer);
        };
        const onEsc = (/** @type {KeyboardEvent} */ e) => {
          if (e.key !== "Escape") return;
          e.stopImmediatePropagation();
          finish(false);
        };
        const ok = el("button", { type: "button", class: "ixe-btn primary", text: "Enviar correo", onclick: () => finish(true) });
        const back = el(
          "div",
          { class: "ixe-confirm-back", onclick: (/** @type {Event} */ e) => e.target === back && finish(false) },
          el(
            "div",
            { class: "ixe-confirm", role: "alertdialog", "aria-modal": "true", "aria-label": "Confirmar envío" },
            el("span", { class: "ixe-confirm-icon" }, icon("send")),
            el("h3", { text: "Confirmar envío" }),
            el("p", { text: text }),
            el("div", { class: "ixe-confirm-actions" }, el("button", { type: "button", class: "ixe-btn", text: "Cancelar", onclick: () => finish(false) }), ok),
          ),
        );
        document.addEventListener("keydown", onEsc, true);
        dialog.append(back);
        ok.focus();
      });
    },
    sendButton: send,
  };
}

/** @param {HTMLElement} box @param {any} g @param {any} h */
export function paintGmail(box, g, h) {
  const head = el("div", { class: "ixe-card-head" }, el("span", { class: "ixe-num", text: "4" }), el("h3", { text: "Hilo de Gmail" }), el("span", { class: "hint" }, icon("info"), "Se responde a todos en el hilo del proyecto."));
  if (!g.connected) {
    box.replaceChildren(head, el("div", { class: "ixe-conn" }, el("span", {}, icon("mail"), "Conecta tu cuenta de Beecker para ver los hilos y crear el correo desde tu Gmail."), el("button", { type: "button", class: "ixe-btn primary", text: "Conectar con Google", onclick: h.connect })), ...(g.error ? [el("div", { class: "ixe-err", text: g.error })] : []));
    return;
  }
  const search = el("input", { id: "ixe-tq", placeholder: "Filtrar hilos por nombre…", autocomplete: "off" });
  /** @type {HTMLInputElement} */ (search).value = g.query;
  search.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      h.search(/** @type {HTMLInputElement} */ (search).value);
    }
  });
  search.addEventListener("input", () => h.filter(/** @type {HTMLInputElement} */ (search).value));
  const list = g.loading
    ? el("div", { class: "ixe-empty", text: 'Buscando hilos "Inicio de ..." en tu Gmail…' })
    : !g.threads.length
      ? el("div", { class: "ixe-empty", text: 'No se encontraron hilos. Prueba con otro nombre.' })
      : el(
          "div",
          { class: "ixe-threads" },
          ...g.threads.map((/** @type {any} */ t) => {
            const sel = g.selected === t.id;
            const radio = el("input", { type: "radio", name: "ixe-thread", value: t.id, checked: sel, onchange: () => h.choose(t.id) });
            const tag = t.remembered ? [el("i", { class: "tag mem", text: "Usado antes" })] : t.suggested ? [el("i", { class: "tag sug", text: "Sugerido" })] : [];
            const rcp = sel ? [el("span", { class: "rcp" }, el("b", { text: "Para:" }), " " + ((t.replyTo || []).map(h.short).join(", ") || "—"), el("br"), el("b", { text: "Cc:" }), " " + ((t.replyCc || []).map(h.short).join(", ") || "—"))] : [];
            return el("label", { class: "ixe-thread" + (sel ? " sel" : ""), "data-s": h.norm(t.subject + " " + t.lastFrom) }, radio, el("span", { class: "body" }, el("span", { class: "top" }, el("b", { text: t.subject }), ...tag), el("small", { text: `${h.date(t.lastDate)} · ${h.short(t.lastFrom)} · ${t.participants} personas · ${t.messageCount} mensajes` }), ...rcp));
          }),
        );
  const result = g.result
    ? [el("div", { class: "ixe-okbox" }, icon("check"), el("span", {}, (g.result.mode === "send" ? "Correo enviado en el hilo." : "Borrador creado en tu Gmail.") + " ", el("a", { href: g.result.link, target: "_blank", rel: "noopener noreferrer", text: g.result.mode === "send" ? "Abrir hilo" : "Abrir borrador" })))]
    : [];
  box.replaceChildren(
    head,
    el("div", { class: "ixe-conn ok" }, el("span", {}, icon("check"), "Conectado como ", el("b", { text: g.email })), el("button", { type: "button", class: "ixe-btn small", text: "Cambiar cuenta", onclick: h.disconnect })),
    el("div", { class: "ixe-tsearch" }, el("span", { class: "ixe-input" }, icon("search"), search), el("button", { type: "button", class: "ixe-btn small", text: "Buscar", onclick: () => h.search(/** @type {HTMLInputElement} */ (search).value) })),
    ...(g.error ? [el("div", { class: "ixe-err", text: g.error })] : []),
    list,
    ...result,
  );
  h.filter(g.query);
}

export { fmtDate };
