// @ts-check
// Centro de Comunicación: categorías, filtros, orden y puntos clave. Las reglas
// son las de la pestaña anterior; no toca el DOM.

export const TYPES = ["Aviso", "Lineamiento", "Nuevo proceso", "Cambio", "Otro"];

/** Comunicados del proyecto abierto (o de todos). @param {any[]} items @param {string} project */
export const inScope = (items, project) => items.filter((x) => !project || !x.proyecto || x.proyecto === project);

/** @param {any[]} all */
export const countsByType = (all) => Object.fromEntries(TYPES.map((t) => [t, all.filter((x) => x.categoria === t).length]));

/** @param {any[]} all */
export const projectsOf = (all) => [...new Set(all.map((x) => x.proyecto).filter(Boolean))].sort();

/**
 * @param {any[]} all
 * @param {{tipo: string, proyecto: string, busqueda: string, orden: string}} s
 */
export function visible(all, s) {
  const query = s.busqueda.toLocaleLowerCase("es");
  return all
    .filter((x) => (s.tipo === "Todos" || x.categoria === s.tipo) && (!s.proyecto || x.proyecto === s.proyecto) && (!s.busqueda || [x.titulo, x.resumen, x.contenido, x.autor, x.proyecto].join(" ").toLocaleLowerCase("es").includes(query)))
    .sort((a, b) => (s.orden === "antiguos" ? a.fecha.localeCompare(b.fecha) : b.fecha.localeCompare(a.fecha)));
}

/** Una línea por punto clave, sin viñetas ni numeración. @param {any} text */
export const keyPoints = (text) =>
  String(text || "")
    .split(/\r?\n/)
    .map((t) => t.trim().replace(/^[•*\-\d.)\s]+/, "").trim())
    .filter(Boolean);

/** Texto corto de una fila. @param {any} x */
export const rowSummary = (x) => x.resumen || x.contenido.slice(0, 140);

/** Indicadores de la parte superior. @param {any[]} all @param {Record<string, number>} counts */
export const kpis = (all, counts) => [
  ["Lineamiento", all.length, "Comunicados totales", "Histórico", ""],
  ["Importante", all.filter((x) => x.importante).length, "Importantes", "Requieren atención", "Importante"],
  ["Aviso", counts.Aviso, "Avisos", "Información general", "Aviso"],
  ["Lineamiento", counts.Lineamiento, "Lineamientos", "Vigentes", "Lineamiento"],
  ["Nuevo proceso", counts["Nuevo proceso"], "Nuevos procesos", "Documentación", ""],
  ["Cambio", counts.Cambio, "Cambios", "Recientes", "Cambio"],
];

/** Lo que se envía al guardar. @param {FormData} form @param {string} uid @param {boolean} important */
export function payloadOf(form, uid, important) {
  /** @type {Record<string, any>} */
  const payload = { uid };
  form.forEach((v, k) => {
    payload[k] = v;
  });
  payload.importante = important;
  return payload;
}
