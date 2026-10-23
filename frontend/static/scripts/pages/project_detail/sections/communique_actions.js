// @ts-check
// Botones de comunicados en el Ejecutivo de AER/T&M (Extensión y Cierre).
import { el } from "#app/lib/dom.js";

/**
 * @param {HTMLElement} target
 * @param {{id?: string, nombre?: string} | undefined} project
 * @param {{open: (o: any) => void}} controller
 */
export function prependCommuniqueActions(target, project, controller) {
  target.querySelector(".project-comm-actions")?.remove();
  if (!project || !project.id) return;
  const open = (/** @type {string} */ kind) => controller.open({ projectId: project.id, projectName: project.nombre || "", family: "aer", kind });
  target.prepend(
    el(
      "div",
      { class: "project-comm-actions" },
      el("button", { type: "button", class: "btn", text: "Extensión", onclick: () => open("extension") }),
      el("button", { type: "button", class: "btn", text: "Cierre", onclick: () => open("cierre_aer") }),
    ),
  );
}
