// @ts-check
// Ventana del editor de hitos: solo pinta y devuelve lo que la persona escribe.
import { el } from "#app/lib/dom.js";
import { ICONS, NEW_TYPE, dmyToIso } from "./milestones_model.js";

/** @param {HTMLElement} icon */
function pickIcon(icon) {
  const box = /** @type {HTMLElement} */ (icon.parentElement);
  box.querySelectorAll(".mh-icono-opcion").forEach((item) => {
    item.classList.remove("selected");
    delete (/** @type {HTMLElement} */ (item).dataset.seleccionado);
  });
  icon.classList.add("selected");
  icon.dataset.seleccionado = "1";
}

/**
 * Una fila del formulario. `entries()` entrega las entradas guardadas del tipo.
 * @param {string[]} types
 * @param {(type: string) => any[]} entries
 * @param {{remove: (type: string, index: number) => void}} actions
 */
export function createRow(types, entries, actions) {
  const select = el(
    "select",
    { class: "filter mh-tipo-select" },
    ...types.map((t) => el("option", { value: t, text: t })),
    el("option", { value: NEW_TYPE, text: "➕ Crear tipo nuevo…" }),
  );
  /** @type {HTMLSelectElement} */ (select).value = types.length ? types[0] : NEW_TYPE;
  const warning = el(
    "div",
    { class: "mh-editando-aviso", hidden: true },
    "✏️ Editando entrada existente — ",
    el("span", { class: "mh-cancelar", text: "cancelar edición" }),
  );
  const existing = el("div", { class: "mh-existentes" });
  const newName = el("input", { type: "text", class: "filter mh-tipo-nuevo", placeholder: "Nombre del nuevo tipo (ej. Demo Sprint 3)" });
  const icons = el(
    "div",
    { class: "mh-iconos" },
    // El espacio entre íconos es parte del diseño anterior (separación en línea).
    ...ICONS.flatMap((icon) => [el("span", { class: "mh-icono-opcion", "data-icono": icon, text: icon, onclick: (/** @type {Event} */ e) => pickIcon(/** @type {HTMLElement} */ (e.currentTarget)) }), " "]),
  );
  const newBlock = el(
    "div",
    { class: "mh-bloque-nuevo", hidden: types.length > 0 },
    newName,
    el("div", { class: "mh-ayuda", text: "Elige un ícono:" }),
    icons,
  );
  const date = el("input", { type: "date", class: "filter mh-fecha" });
  const notes = el("textarea", { class: "filter mh-obs", rows: 2 });
  const close = el("span", { class: "mh-quitar", text: "✕" });
  const row = el(
    "div",
    { class: "mh-fila" },
    close,
    warning,
    el("label", { text: "Tipo de hito" }),
    select,
    existing,
    newBlock,
    el("label", { class: "mh-etiqueta-fecha", text: "Fecha" }),
    date,
    el("label", { text: "Observaciones (no se muestran en el Gantt)" }),
    notes,
  );
  close.addEventListener("click", () => row.remove());

  const clearEdit = () => {
    delete row.dataset.editTipo;
    delete row.dataset.editIndice;
    warning.hidden = true;
  };
  const paintExisting = () => {
    const type = /** @type {HTMLSelectElement} */ (select).value;
    existing.replaceChildren();
    if (type === NEW_TYPE) return;
    const items = entries(type);
    if (!items.length) {
      existing.append(el("div", { class: "mh-vacio", text: "Sin registros previos de este tipo." }));
      return;
    }
    existing.append(
      el("div", { class: "mh-titulo", text: "Entradas ya guardadas (clic en ✏️ para editar):" }),
      ...items.map((h) =>
        el(
          "div",
          { class: "mh-existente" },
          el("span", { class: "mh-texto", text: h.fecha + (h.observacion ? " — " + h.observacion.substring(0, 30) : "") }),
          el("span", { class: "mh-accion", title: "Editar", text: "✏️", onclick: () => edit(type, h.indice, dmyToIso(h.fecha), h.observacion) }),
          el("span", { class: "mh-accion", title: "Eliminar", text: "🗑️", onclick: () => actions.remove(type, h.indice) }),
        ),
      ),
    );
  };
  /** @param {string} type @param {number} index @param {string} iso @param {string} [note] */
  const edit = (type, index, iso, note) => {
    /** @type {HTMLInputElement} */ (date).value = iso;
    /** @type {HTMLTextAreaElement} */ (notes).value = note || "";
    row.dataset.editTipo = type;
    row.dataset.editIndice = String(index);
    warning.hidden = false;
  };
  select.addEventListener("change", () => {
    newBlock.hidden = /** @type {HTMLSelectElement} */ (select).value !== NEW_TYPE;
    clearEdit();
    paintExisting();
  });
  /** @type {HTMLElement} */ (warning.querySelector(".mh-cancelar")).addEventListener("click", clearEdit);
  if (types.length) paintExisting();
  const first = /** @type {HTMLElement | null} */ (icons.querySelector(".mh-icono-opcion"));
  if (first) pickIcon(first);

  return {
    node: row,
    paintExisting,
    edit,
    /** Fija el tipo y deja la fila lista para editar esa entrada. @param {string} type */
    select(type) {
      /** @type {HTMLSelectElement} */ (select).value = type;
      select.dispatchEvent(new Event("change"));
    },
    typeValue: () => /** @type {HTMLSelectElement} */ (select).value,
    read() {
      const icon = /** @type {HTMLElement | null} */ (icons.querySelector('[data-seleccionado="1"]'));
      return {
        tipo: /** @type {HTMLSelectElement} */ (select).value,
        nuevoNombre: /** @type {HTMLInputElement} */ (newName).value,
        icono: icon ? /** @type {string} */ (icon.dataset.icono) : "📌",
        fecha: /** @type {HTMLInputElement} */ (date).value,
        obs: /** @type {HTMLTextAreaElement} */ (notes).value,
        editTipo: row.dataset.editTipo,
        editIndice: row.dataset.editIndice === undefined ? undefined : Number(row.dataset.editIndice),
      };
    },
  };
}

/** @param {{close: () => void, add: () => void, save: () => void}} handlers */
export function createDialog(handlers) {
  const rows = el("div", { id: "mh-filas-container" });
  const error = el("div", { id: "mh-error", hidden: true });
  const save = el("button", { class: "btn btn-primary", id: "mh-btn-guardar", type: "button", text: "Guardar", onclick: handlers.save });
  const overlay = el(
    "div",
    { id: "modal-hito-overlay", onclick: (/** @type {Event} */ e) => e.target === overlay && handlers.close() },
    el(
      "div",
      { class: "mh-modal", role: "dialog", "aria-modal": "true", "aria-label": "Agregar hitos" },
      el("div", { class: "mh-cabecera" }, el("div", { class: "mh-titulo-modal", text: "+ Agregar Hito(s)" }), el("span", { class: "mh-cerrar", text: "✕", onclick: handlers.close })),
      rows,
      el("button", { class: "btn mh-agregar", type: "button", text: "+ Agregar otro hito", onclick: handlers.add }),
      error,
      el("div", { class: "mh-pie" }, el("button", { class: "btn", type: "button", text: "Cancelar", onclick: handlers.close }), save),
    ),
  );
  return {
    overlay,
    rows,
    /** @param {string} [message] */
    showError(message) {
      error.textContent = message || "";
      error.hidden = !message;
    },
    /** @param {boolean} busy */
    busy(busy) {
      /** @type {HTMLButtonElement} */ (save).disabled = busy;
      save.textContent = busy ? "Guardando..." : "Guardar";
    },
  };
}
