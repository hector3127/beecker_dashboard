// @ts-check
// Initial dashboards and deferred executive reads; other tab actions stay RPC.
import { apiGet } from "#app/data/api-client.js";

/** @param {typeof apiGet} [get] */
export function createProjectData(get = apiGet) {
  const read = async (path) =>
    (await get(path, undefined, { timeout: 90000 })).data;
  return {
    filters: () => read("screens/proyectos/filtros/"),
    raid: (id) => read(`screens/proyectos/${encodeURIComponent(id)}/raid/`),
    tasks: (id) => read(`screens/proyectos/${encodeURIComponent(id)}/tasks/`),
    stages: (id) => read(`screens/proyectos/${encodeURIComponent(id)}/etapas/`),
    resources: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/recursos/`),
    /** @param {string} id @param {boolean} aer */
    dashboard: (id, aer) =>
      read(
        `screens/proyectos/${encodeURIComponent(id)}/${aer ? "aer" : "ejecutivo"}/`,
      ),
  };
}
