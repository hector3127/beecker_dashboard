import { el } from "#app/lib/dom.js";

// Transport only: the shared AER/IXS presentation and editors are migrated next.
export function createClientActionsLoader(api) {
  let request = 0;
  return {
    async load({ project, target, cache, tab, current, apply }) {
      const id = project?.proyecto?.id;
      if (!id || !target) return;
      const token = ++request;
      const active = () => token === request && current(id);
      const cached = cache[id];
      if (cached?.proyecto) {
        apply(cached);
        return;
      }
      const message = (text) =>
        target.replaceChildren(
          el("div", {
            class: "ixs-card",
            style: { padding: "22px" },
            text,
          }),
        );
      message(
        "Cargando información de " +
          (tab === "cliente" ? "cliente" : "acciones") +
          "…",
      );
      try {
        const result = await api.client(id);
        if (!active()) return;
        if (!result?.ok || String(result.proyectoId) !== String(id)) {
          message(
            "No se pudieron cargar los datos de Cliente y Acciones: " +
              (result?.error || "respuesta de proyecto inválida"),
          );
          return;
        }
        result.proyecto = project.proyecto;
        cache[id] = result;
        apply(result);
      } catch (error) {
        if (active())
          target.textContent =
            "No se pudo consultar Cliente y Acciones: " +
            (error?.message || String(error));
      }
    },
  };
}
