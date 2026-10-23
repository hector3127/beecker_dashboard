import { el, svg } from "#app/lib/dom.js";
import { months, num } from "./model.js";

export { el, svg };
export const node = (tag, cls, ...children) =>
  el(
    tag,
    { class: cls },
    ...children.flat(Infinity).filter((v) => v !== null && v !== undefined),
  );
export const text = (tag, value, cls) => el(tag, { class: cls, text: value });
export const button = (label, run, cls = "", attrs = {}) =>
  el("button", { type: "button", class: cls, onclick: run, ...attrs }, label);
export const input = (attrs, run, event = "change") =>
  el("input", { ...attrs, ["on" + event]: (e) => run(e.target.value) });
export function select(items, value, run, attrs = {}) {
  const result = el(
    "select",
    { ...attrs, onchange: (e) => run(e.target.value) },
    ...items.map(([value, label]) => el("option", { value, text: label })),
  );
  result.value = String(value);
  return result;
}
export const monthSelect = (value, run, attrs = {}) =>
  select(
    [[-1, "Todos los meses"], ...months.map((m, i) => [i, m])],
    value,
    run,
    attrs,
  );
export const label = (name, control) => node("label", null, name, control);
export const styled = (tag, cls, style, ...children) =>
  el(tag, { class: cls, style }, ...children);
export const heading = (name, symbol = "bars") =>
  node("h3", null, icon(symbol), " " + name);
export const track = (width, color) =>
  node(
    "div",
    "gm-track",
    styled("i", null, { width: width + "%", background: color }),
  );
export const legend = (series) =>
  node(
    "div",
    "ga-chart-legend",
    series.map(([name, color]) =>
      node("span", null, styled("i", null, { background: color }), name),
    ),
  );
export function table(head, rows, cls = "gm-table") {
  return node(
    "table",
    cls,
    node(
      "thead",
      null,
      node(
        "tr",
        null,
        head.map((h) => text("th", h)),
      ),
    ),
    node("tbody", null, rows),
  );
}
export const cell = (value, cls, percent = false, tag = "td") =>
  text(
    tag,
    value == null
      ? "NA"
      : typeof value === "string"
        ? value
        : num(value) + (percent ? "%" : ""),
    cls,
  );
export function download(rows, name, separator = "\r\n") {
  const content =
    "\uFEFF" +
    rows
      .map((row) =>
        row.map((v) => '"' + String(v).replace(/"/g, '""') + '"').join(","),
      )
      .join(separator);
  const url = URL.createObjectURL(
    new Blob([content], { type: "text/csv;charset=utf-8;" }),
  );
  const link = el("a", { href: url, download: name });
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// The icon paths are static assets; dynamic values never enter markup.
import { paths } from "./icons.js";
export function icon(name) {
  return svg(
    "svg",
    {
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": 1.8,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
      "aria-hidden": true,
    },
    ...(paths[name] || paths.bars).map(([tag, attrs]) => svg(tag, attrs)),
  );
}
