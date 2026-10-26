// @ts-check
// model: eva3/history_reference. Original data, ordering and interactions are preserved.
/**
 * @param {any} value
 */
export const normalize = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
/**
 * @param {string} text
 */
export const dateValue = (text) => {
  const m = text.trim().match(/^(\d{2})\/(\d{2})\/(\d{2}|\d{4})$/);
  return m ? `${m[3].length === 2 ? "20" : ""}${m[3]}-${m[2]}-${m[1]}` : "";
};
/**
 * @param {any} value
 */
export const csvCell = (value) => {
  let text = String(value ?? "");
  if (/^[=+@-]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
};
/**
 * @param {any} value
 */
export const status = (value) =>
  ["completed", "completado", "finalizado"].includes(normalize(value))
    ? "Finalizado"
    : ["cancelled", "canceled", "cancelado"].includes(normalize(value))
      ? "Cancelado"
      : value || "Sin dato";
