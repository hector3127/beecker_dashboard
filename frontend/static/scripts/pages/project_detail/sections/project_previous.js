import { el } from "#app/lib/dom.js";

// Preserve the temporary IXS → generic executive → IXS navigation.
export function createProjectPrevious(store, services) {
  const controller = {
    back(id) {
      if (!store.ixs || store.ixs.proyecto.id !== id) return;
      store.ixsTab = "resumen";
      services.mountIxs();
    },
    open() {
      const project = store.ixs;
      if (!project?.proyecto) return;
      const id = project.proyecto.id;
      services.executive.mount(project);
      const target = document.getElementById("dashboard-proyecto-detalle");
      if (target)
        target.prepend(
          el(
            "div",
            { class: "ixs-shell project-previous-return" },
            el(
              "button",
              { class: "ixs-btn primary", onclick: () => controller.back(id) },
              "← Volver al nuevo ejecutivo",
            ),
          ),
        );
    },
  };
  return controller;
}
