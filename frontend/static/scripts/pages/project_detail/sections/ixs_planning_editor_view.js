import { el } from "#app/lib/dom.js";
import { planningEditorModel } from "./ixs_planning_editor_model.js";

export function planningEditor(type, uid, initialType, state, actions) {
  const model = planningEditorModel(type, uid, initialType, state);
  const button = (text, action, cls = "ixs-btn") =>
    el("button", { type: "button", class: cls, onclick: action }, text);
  const error = el("div", {
    id: "ixs-plan-error",
    class: "ixs-plan-editor-error",
  });
  const saveButton = el(
    "button",
    { type: "submit", class: "ixs-btn primary" },
    "Guardar",
  );
  const deleteButton = uid ? button("Eliminar", actions.delete) : null;
  const form = el(
    "form",
    { id: "ixs-plan-form", onsubmit: actions.save },
    ...model.fields.map((field) =>
      el(
        "label",
        {},
        field.label,
        field.options
          ? el(
              "select",
              { name: field.name },
              ...field.options.map((option) =>
                el(
                  "option",
                  {
                    selected: field.value === option,
                  },
                  option,
                ),
              ),
            )
          : el("input", {
              name: field.name,
              type: field.inputType,
              value: field.value,
              required: field.required,
            }),
      ),
    ),
    error,
    el(
      "div",
      { class: "ixs-plan-editor-actions" },
      ...(deleteButton ? [deleteButton] : []),
      button("Cancelar", actions.close),
      saveButton,
    ),
  );
  const modal = el(
    "div",
    {
      id: "ixs-plan-modal",
      class: "ixs-clockify-modal",
      dataset: { renderer: "modular-planning-editor" },
    },
    el(
      "div",
      {
        class: "ixs-clockify-dialog ixs-recurso-dialog",
        role: "dialog",
        "aria-modal": "true",
        "aria-labelledby": "ixs-plan-editor-title",
      },
      el(
        "div",
        { class: "ixs-section-head" },
        el("h3", { id: "ixs-plan-editor-title" }, model.title),
        button("✕", actions.close),
      ),
      form,
    ),
  );
  modal.addEventListener("click", (event) => {
    if (event.target === modal) actions.close();
  });
  document.body.append(modal);
  return { modal, form, error, saveButton, deleteButton };
}
