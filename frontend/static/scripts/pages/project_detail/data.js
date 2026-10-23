// @ts-check
// Migrated project reads and actions; remaining tabs still use RPC.
import { apiGet, apiSend } from "#app/data/api-client.js";

/** @param {typeof apiGet} [get] @param {typeof apiSend} [send] */
export function createProjectData(get = apiGet, send = apiSend) {
  const read = async (path) =>
    (await get(path, undefined, { timeout: 90000 })).data;
  return {
    filters: () => read("screens/proyectos/filtros/"),
    raid: (id) => read(`screens/proyectos/${encodeURIComponent(id)}/raid/`),
    tasks: (id) => read(`screens/proyectos/${encodeURIComponent(id)}/tasks/`),
    records: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/registros/`),
    stages: (id) => read(`screens/proyectos/${encodeURIComponent(id)}/etapas/`),
    resources: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/recursos/`),
    planning: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/planeacion/`),
    planningAzure: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/planeacion/azure/`),
    saveWorkItem: async (id, campo, valor) =>
      (
        await send(
          "POST",
          `screens/work-items/${encodeURIComponent(id)}/avance/`,
          { campo, valor },
          { timeout: 90000 },
        )
      ).data,
    commentWorkItem: async (id, comentario) =>
      (
        await send(
          "POST",
          `screens/work-items/${encodeURIComponent(id)}/comentarios/`,
          { comentario },
          { timeout: 90000 },
        )
      ).data,
    savePlan: async (type, payload) =>
      (
        await send(
          "POST",
          `screens/proyectos/${encodeURIComponent(payload.idProyecto)}/planeacion/${encodeURIComponent(type)}/guardar/`,
          payload,
          { timeout: 90000 },
        )
      ).data,
    deletePlan: async (type, id, uid) =>
      (
        await send(
          "POST",
          `screens/proyectos/${encodeURIComponent(id)}/planeacion/${encodeURIComponent(type)}/eliminar/`,
          { uid },
          { timeout: 90000 },
        )
      ).data,
    saveResource: async (id, payload) =>
      (
        await send(
          "POST",
          `screens/proyectos/${encodeURIComponent(id)}/recursos/guardar/`,
          payload,
          { timeout: 90000 },
        )
      ).data,
    /** @param {string} id @param {boolean} aer */
    dashboard: (id, aer) =>
      read(
        `screens/proyectos/${encodeURIComponent(id)}/${aer ? "aer" : "ejecutivo"}/`,
      ),
  };
}
