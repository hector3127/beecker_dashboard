// @ts-check
// model: operativa/sections/eva. Original data, ordering and interactions are preserved.
export const NO_VALUE = "—";
export const RESTRICTED =
  "Cifras del equipo completo: no disponibles con tu acceso.";
/**
 * @param {any} value
 */
export const known = (value) =>
  typeof value === "number" && Number.isFinite(value);
