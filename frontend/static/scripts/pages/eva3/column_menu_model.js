// @ts-check
// model: eva3/column_menu. Original data, ordering and interactions are preserved.
/**
 * @param {any} value
 */
export const normalize = (value) =>
  String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
/**
 * @param {string} raw
 * @param {any} value
 * @param {string} color
 * @param {any} filter
 */
export function matchesColumn(raw, value, color, filter) {
  if (!filter) return true;
  if (filter.values && !filter.values.has(raw)) return false;
  if (filter.color && color !== filter.color) return false;
  const { condition: op, first, second } = filter;
  if (!op) return true;
  if (op === "empty") return raw === "";
  if (op === "notempty") return raw !== "";
  if (op === "contains") return normalize(raw).includes(normalize(first));
  if (op === "notcontains") return !normalize(raw).includes(normalize(first));
  if (op === "textis") return normalize(raw) === normalize(first);
  if (op === "textnot") return normalize(raw) !== normalize(first);
  if (value === null || first === "") return false;
  const a = typeof value === "number" ? Number(first) : first,
    b = typeof value === "number" ? Number(second) : second;
  return op === "eq"
    ? value === a
    : op === "gt"
      ? value > a
      : op === "gte"
        ? value >= a
        : op === "lt"
          ? value < a
          : op === "lte"
            ? value <= a
            : op === "between"
              ? second !== "" && value >= a && value <= b
              : true;
}
