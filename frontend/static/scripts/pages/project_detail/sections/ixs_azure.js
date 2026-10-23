import { azurePanel } from "./ixs_azure_model.js";
import { azureMessage } from "./ixs_azure_loading.js";

// Transitional controller: data and loading are modular; the existing summary,
// grouping and Work Item renderers stay independent for visual comparison.
export function createAzureController(api) {
  let session;
  return {
    async load(root, project, state, force, lifecycle) {
      const owner = {};
      session = owner;
      const id = project.proyecto.id;
      const token = ++state.requestId;
      state.projectId = id;
      state.error = "";
      const current = () =>
        session === owner &&
        root.isConnected &&
        state.requestId === token &&
        lifecycle.current(project) &&
        lifecycle.active();
      azureMessage(root, "Cargando Azure DevOps…");
      try {
        const result = await api.azure(id, !!force);
        if (!current()) return;
        if (!result || !result.ok) {
          azureMessage(
            root,
            `No se pudo cargar Azure para ${id}: ${result?.error || "Respuesta inesperada"}`,
            true,
          );
          return;
        }
        lifecycle.loaded(azurePanel(result, id, token));
      } catch (error) {
        if (!current()) return;
        azureMessage(
          root,
          "Error al consultar Azure DevOps: " +
            (error?.message || String(error)),
        );
      }
    },
  };
}
