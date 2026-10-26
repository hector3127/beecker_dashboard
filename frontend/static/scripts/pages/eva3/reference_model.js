// @ts-check
// model: eva3/reference. Original data, ordering and interactions are preserved.
/**
 * @param {any} value
 */
export const csvCell = (value) => {
  let text = String(value ?? "");
  if (/^[=+@-]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
};
