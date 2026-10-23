// @ts-check
// Aviso de datos que faltan o que vienen de otra hoja (proyecto.datosFaltantes).
import { el } from "#app/lib/dom.js";

/** @param {HTMLElement} target @param {{datosFaltantes?: string[]} | undefined} project */
export function prependDataNotice(target, project) {
  const notes = (project && project.datosFaltantes) || [];
  target.querySelector(".project-data-notice")?.remove();
  if (!notes.length) return;
  target.prepend(
    el(
      "div",
      { class: "project-data-notice", role: "status" },
      el("strong", { text: "Datos del proyecto" }),
      el("ul", {}, ...notes.map((text) => el("li", { text }))),
    ),
  );
}
