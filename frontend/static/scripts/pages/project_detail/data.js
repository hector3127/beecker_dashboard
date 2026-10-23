// @ts-check
// Migrated project reads and actions; remaining tabs still use RPC.
import { apiGet, apiSend } from "#app/data/api-client.js";

/** @param {typeof apiGet} [get] @param {typeof apiSend} [send] */
export function createProjectData(get = apiGet, send = apiSend) {
  const read = async (path) =>
    (await get(path, undefined, { timeout: 90000 })).data;
  const aiPost = async (id, path, payload) =>
    (
      await send(
        "POST",
        `screens/proyectos/${encodeURIComponent(id)}/ia/${path}/`,
        payload,
        { timeout: 90000 },
      )
    ).data;
  return {
    aiAnalyze: (id, contexto, forzar) =>
      aiPost(id, "analizar", { contexto, forzar }),
    aiAsk: (id, contexto, pregunta) =>
      aiPost(id, "preguntar", { contexto, pregunta }),
    aiSaveMemory: (id, snapshot, analisis) =>
      aiPost(id, "memoria/guardar", { snapshot, analisis }),
    aiSaveMinute: (id, tema, fecha, contenido) =>
      aiPost(id, "minutas/guardar", { tema, fecha, contenido }),
    aiSaveFolder: (id, url, tipo) =>
      aiPost(id, "drive/carpetas/guardar", { url, tipo }),
    aiRemoveFolder: (id, carpeta, tipo) =>
      aiPost(id, "drive/carpetas/quitar", { carpeta, tipo }),
    aiReadDocument: (id, archivo) =>
      aiPost(id, "drive/documento/leer", { archivo }),
    aiGenerateMinute: (id, archivos, tema, fecha, notas) =>
      aiPost(id, "drive/minuta/generar", { archivos, tema, fecha, notas }),
    aiSaveAction: (id, payload) => aiPost(id, "accion/guardar", payload),
    filters: () => read("screens/proyectos/filtros/"),
    client: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/cliente/`),
    aiAnalysis: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/ia/analisis/`),
    aiMemory: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/ia/memoria/`),
    aiMinutes: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/ia/minutas/`),
    aiDriveFolders: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/ia/drive/carpetas/`),
    aiDriveFiles: (id) =>
      read(`screens/proyectos/${encodeURIComponent(id)}/ia/drive/archivos/`),
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
    azure: async (id, force = false) =>
      (
        await get(
          `screens/proyectos/${encodeURIComponent(id)}/azure/`,
          force ? { forzar: "1" } : undefined,
          { timeout: 90000 },
        )
      ).data,
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
    raidRegistry: async (id, force) =>
      (
        await get(
          `screens/proyectos/${encodeURIComponent(id)}/raid-registro/`,
          force ? { forzar: "1" } : undefined,
          { timeout: 90000 },
        )
      ).data,
    raidPrompt: (tipo) =>
      read(`screens/proyectos/raid/prompt/?tipo=${encodeURIComponent(tipo)}`),
    raidFieldTypes: (id, tipo) =>
      read(
        `screens/proyectos/${encodeURIComponent(id)}/raid/campos/?tipo=${encodeURIComponent(tipo)}`,
      ),
    raidCreationOptions: (id, tipo) =>
      read(
        `screens/proyectos/${encodeURIComponent(id)}/raid/alta-opciones/?tipo=${encodeURIComponent(tipo)}`,
      ),
    saveRaidPrompt: async (tipo, prompt) =>
      (
        await send(
          "POST",
          "screens/proyectos/raid/prompt/",
          { tipo, prompt },
          { timeout: 90000 },
        )
      ).data,
    suggestRaid: async (tipo, descripcion) =>
      (
        await send(
          "POST",
          "screens/proyectos/raid/sugerir/",
          { tipo, descripcion },
          { timeout: 90000 },
        )
      ).data,
    createRaid: async (id, tipo, datos) =>
      (
        await send(
          "POST",
          `screens/proyectos/${encodeURIComponent(id)}/raid/crear/`,
          { tipo, datos },
          { timeout: 90000 },
        )
      ).data,
    communications: () => read("screens/proyectos/comunicados/"),
    saveCommunication: async (payload) =>
      (
        await send(
          "POST",
          "screens/proyectos/comunicados/guardar/",
          payload,
          { timeout: 90000 },
        )
      ).data,
    milestoneTypes: () => read("screens/proyectos/hitos/tipos/"),
    saveMilestones: async (id, hitos) =>
      (
        await send(
          "POST",
          `screens/proyectos/${encodeURIComponent(id)}/hitos/guardar/`,
          { hitos },
          { timeout: 90000 },
        )
      ).data,
    editMilestone: async (id, payload) =>
      (
        await send(
          "POST",
          `screens/proyectos/${encodeURIComponent(id)}/hitos/editar/`,
          payload,
          { timeout: 90000 },
        )
      ).data,
    deleteMilestone: async (id, tipo, indice) =>
      (
        await send(
          "POST",
          `screens/proyectos/${encodeURIComponent(id)}/hitos/eliminar/`,
          { tipo, indice },
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
