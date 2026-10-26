import { el } from "#app/lib/dom.js";

export function riskDialog(handlers) {
  const description = el("textarea", {
    id: "mr-descripcion",
    class: "filter gr-description",
    rows: 3,
  });
  const select = (id, options, selected) => {
    const node = el(
      "select",
      { id, class: "filter gr-select" },
      ...options.map((value) => el("option", { value }, value)),
    );
    node.value = selected;
    return node;
  };
  const impact = select("mr-impacto", ["Alto", "Medio", "Bajo"], "Medio");
  const probability = select(
    "mr-probabilidad",
    ["Alta", "Media", "Baja"],
    "Media",
  );
  const owner = el("input", {
    id: "mr-responsable",
    type: "text",
    class: "filter gr-owner",
  });
  const error = el("div", { id: "mr-error", class: "gr-error" });
  const button = el(
    "button",
    { id: "mr-btn-guardar", class: "btn btn-primary", onclick: handlers.save },
    "Guardar",
  );
  const label = (text, id) => el("label", { class: "gr-label", for: id }, text);
  const panel = el(
    "div",
    {
      class: "gr-panel",
      role: "dialog",
      "aria-modal": "true",
      "aria-labelledby": "gr-title",
    },
    el(
      "div",
      { class: "gr-head" },
      el("div", { class: "gr-title", id: "gr-title" }, "⚠ Agregar Riesgo"),
      el("span", { class: "gr-close", onclick: handlers.close }, "✕"),
    ),
    label("Descripción", description.id),
    description,
    label("Impacto", impact.id),
    impact,
    label("Probabilidad", probability.id),
    probability,
    label("Responsable (opcional)", owner.id),
    owner,
    error,
    el(
      "div",
      { class: "gr-actions" },
      el("button", { class: "btn", onclick: handlers.close }, "Cancelar"),
      button,
    ),
  );
  const overlay = el(
    "div",
    {
      id: "modal-riesgo-overlay",
      class: "gr-overlay",
      onclick: (event) => {
        if (event.target === overlay) handlers.close();
      },
    },
    panel,
  );
  return {
    overlay,
    values: () => ({
      descripcion: description.value,
      impacto: impact.value,
      probabilidad: probability.value,
      responsable: owner.value,
    }),
    busy(value) {
      button.disabled = value;
      button.textContent = value ? "Guardando..." : "Guardar";
    },
    message(text) {
      error.textContent = text;
      error.classList.toggle("gr-error-visible", !!text);
    },
  };
}
