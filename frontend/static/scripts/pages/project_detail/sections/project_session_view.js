import { el } from "#app/lib/dom.js";

export function aerError(target, message) {
  target.replaceChildren(
    el(
      "div",
      { class: "card" },
      el("h3", {}, "PROYECTO AER / T&M"),
      el(
        "div",
        { style: { color: "var(--rojo)" } },
        message || "No se pudo cargar el proyecto.",
      ),
    ),
  );
}
export function ixsError(target, message) {
  target.replaceChildren(
    el("div", { class: "card" }, message || "No se pudo cargar el ejecutivo."),
  );
}
export function outdatedNotice(target) {
  target?.prepend(
    el(
      "div",
      { class: "aer-callout red", style: { marginBottom: "10px" } },
      el("b", {}, "Backend AER desactualizado."),
      " Las horas vienen de Clockify, pero Planeación/Riesgos/Salud por dimensión requieren reemplazar AERTYMProyectoService.gs por la versión V3.",
    ),
  );
}
