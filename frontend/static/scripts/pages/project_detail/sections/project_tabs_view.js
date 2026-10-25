import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";

export function placeholder(target, tab, actions) {
  const names = {
    planeacion: "Planeación",
    recursos: "Recursos",
    riesgos: "Riesgos",
    azure: "Azure DevOps",
  };
  target.replaceChildren(
    el(
      "div",
      { class: "ixs-card ixs-placeholder" },
      icon("folder"),
      el("h3", {}, names[tab] || "Apartado"),
      el(
        "p",
        {},
        "Prepararemos esta pestaña en la siguiente etapa. Puedes consultar los mismos datos en la vista ejecutiva anterior mientras tanto.",
      ),
      el(
        "button",
        { class: "ixs-btn primary", onclick: () => actions.select("resumen") },
        "Volver al ejecutivo",
      ),
      " ",
      el(
        "button",
        { class: "ixs-btn", onclick: actions.previous },
        "Consultar vista anterior →",
      ),
    ),
  );
}
