import { el } from "#app/lib/dom.js";
export { el };
export { dateText } from "./actions_model.js";
export const text = (value) => (value == null ? "" : String(value));
export const h = (tag, cls, ...children) =>
  el(
    tag,
    cls ? { class: cls } : {},
    ...children.flat().filter((x) => x != null),
  );
export const div = (cls, ...children) => h("div", cls, ...children);
export const styled = (node, css) => {
  Object.assign(node.style, css);
  return node;
};
export const button = (label, onclick, cls = "aer-btn", props = {}) =>
  el("button", { class: cls, onclick, ...props }, label);
export const cell = (...body) => h("td", "", ...body);
export const table = (cls, headers, rows, empty) =>
  h(
    "table",
    cls,
    h(
      "thead",
      "",
      h(
        "tr",
        "",
        ...headers.map((t) => (typeof t === "string" ? h("th", "", t) : t)),
      ),
    ),
    h(
      "tbody",
      "",
      ...(rows.length
        ? rows
        : [h("tr", "", el("td", { colspan: headers.length }, empty))]),
    ),
  );
export function input(value, props = {}) {
  const node = el("input", props);
  node.value = text(value);
  return node;
}
