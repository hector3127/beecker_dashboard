// @ts-check
// Only initial project reads have moved. Tab actions still use their old services.
import { apiGet } from "#app/data/api-client.js";

/** @param {typeof apiGet} [get] */
export function createProjectData(get = apiGet) {
  const read = async (path) =>
    (await get(path, undefined, { timeout: 90000 })).data;
  return {
    filters: () => read("screens/proyectos/filtros/"),
    /** @param {string} id @param {boolean} aer */
    dashboard: (id, aer) =>
      read(
        `screens/proyectos/${encodeURIComponent(id)}/${aer ? "aer" : "ejecutivo"}/`,
      ),
  };
}
