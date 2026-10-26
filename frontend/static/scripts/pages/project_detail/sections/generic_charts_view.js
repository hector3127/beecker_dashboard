import { el } from "#app/lib/dom.js";
const div = (cls, ...children) => el("div", { class: cls }, ...children);
const empty = () => div("gc-empty", "Sin datos disponibles.");
const svg = (tag, props, ...children) => {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(props))
    node.setAttribute(key, String(value));
  node.append(...children);
  return node;
};
export function areaView(model) {
  if (!model.areas.length) return empty();
  const ring = svg(
    "svg",
    { width: 180, height: 180, viewBox: "0 0 180 180", class: "gc-donut" },
    ...model.areas.map((row) =>
      svg("circle", {
        cx: 90,
        cy: 90,
        r: 77,
        fill: "none",
        stroke: row.color,
        "stroke-width": 26,
        "stroke-dasharray": row.dash,
        "stroke-dashoffset": row.offset,
        transform: "rotate(-90 90 90)",
      }),
    ),
    svg(
      "text",
      {
        x: 90,
        y: 86,
        "text-anchor": "middle",
        class: "donut-center-value gc-center",
      },
      String(model.total),
    ),
    svg(
      "text",
      { x: 90, y: 106, "text-anchor": "middle", class: "gc-total-label" },
      "Hrs Totales",
    ),
  );
  const legend = div(
    "gc-area-legend",
    ...model.areas.map((row) =>
      div(
        "donut-legend-row",
        el("span", { class: "donut-dot", style: { background: row.color } }),
        el("span", { class: "donut-legend-name", title: row.name }, row.name),
        el("span", { class: "donut-legend-val" }, row.hours),
        el("span", { class: "donut-legend-pct" }, row.pct),
      ),
    ),
  );
  return div("gc-area", el("div", {}, ring), legend);
}
const bar = (row) =>
  div(
    "gc-row",
    div(
      "gc-bar-head",
      el("span", { class: "gc-name" }, row.name),
      el("span", { class: "gc-hours" }, row.hours),
    ),
    div(
      "barra-track gc-track gc-estimated-track",
      el("div", {
        class: "barra-fill gc-estimated",
        style: { width: row.estimated + "%" },
      }),
    ),
    div(
      "barra-track gc-track",
      el("div", {
        class: "barra-fill gc-real",
        style: { width: row.real + "%" },
      }),
    ),
  );
export function barsView(items, expandable, id) {
  const root = document.createDocumentFragment();
  if (!items.length) {
    root.append(empty());
    return { root };
  }
  const visible = expandable ? items.slice(0, 5) : items,
    extra = expandable ? items.slice(5) : [];
  root.append(...visible.map(bar));
  let hidden, link;
  if (extra.length) {
    hidden = el(
      "div",
      { id: id + "-ocultos", class: "gc-hidden" },
      ...extra.map(bar),
    );
    link = el(
      "a",
      { href: "#", id: id + "-toggle", class: "gc-toggle" },
      `Ver todos (${extra.length} más)`,
    );
    root.append(hidden, div("gc-toggle-wrap", link));
  }
  root.append(
    div(
      "gc-legend" + (expandable ? " gc-more-legend" : ""),
      el("span", {}, el("span", { class: "gc-key gc-estimated" }), "Estimadas"),
      el("span", {}, el("span", { class: "gc-key gc-real" }), "Reales"),
    ),
  );
  return { root, hidden, link, extra: extra.length };
}
