// @ts-check
// DOM presentation; state and reload callbacks belong to the controller.
import { el, svg } from "#app/lib/dom.js";
import { fmt } from "./reference_model.js";

/** @param {Record<string, any>} ctx Live state and controller callbacks. */
export function renderReference(ctx) {
  ctx.percent.setAttribute("aria-pressed", String(ctx.mode === "percent"));
  ctx.hours.setAttribute("aria-pressed", String(ctx.mode === "hours"));
  const values = ctx.months.map(ctx.amount),
    valid = values.filter((value) => value !== null && Number.isFinite(value)),
    average = valid.length
      ? valid.reduce((a, b) => a + b, 0) / valid.length
      : null;
  const top =
    ctx.mode === "percent"
      ? Math.max(100, Math.ceil(Math.max(0, ...valid) / 25) * 25)
      : Math.max(1, Math.ceil(Math.max(0, ...valid) / 1000) * 1000);
  const W = Math.max(700, ctx.plot.clientWidth),
    H = ctx.section.classList.contains("bill-chart-expanded")
      ? Math.max(260, window.innerHeight - 200)
      : 220,
    base = H - 30,
    height = H - 55,
    start = 46,
    slot = (W - 58) / Math.max(1, ctx.months.length);
  const root = svg("svg", {
    id: "bill-chart",
    viewBox: `0 0 ${W} ${H}`,
    height: H,
    role: "group",
    "aria-label":
      ctx.mode === "percent"
        ? "Facturabilidad global por mes"
        : "Horas facturadas por mes",
  });
  root.append(
    svg(
      "defs",
      {},
      svg(
        "linearGradient",
        { id: "bill-bar-active", x2: 0, y2: 1 },
        svg("stop", { offset: "0%", "stop-color": "#8d4dff" }),
        svg("stop", { offset: "100%", "stop-color": "#5021d2" }),
      ),
    ),
  );
  for (let tick = 0; tick <= 4; tick++) {
    const y = base - (tick / 4) * height;
    root.append(
      svg("line", {
        x1: start,
        x2: W - 8,
        y1: y,
        y2: y,
        stroke: "#eee8fc",
        "stroke-width": 1,
      }),
      svg(
        "text",
        {
          x: start - 7,
          y: y + 3,
          "text-anchor": "end",
          fill: "#a08ac2",
          "font-size": 9,
        },
        `${fmt((top * tick) / 4, 0)}${ctx.mode === "percent" ? "%" : ""}`,
      ),
    );
  }
  ctx.months.forEach((month, index) => {
    const value = values[index],
      x = start + index * slot + 5,
      width = slot - 10,
      y = value === null ? base : base - (Math.max(0, value) / top) * height;
    const group = svg("g", {
      role: "button",
      tabindex: 0,
      "aria-label": `${month.label}: ${fmt(value)}${ctx.mode === "percent" ? "%" : " h"}`,
      "aria-pressed": String(ctx.selected === index),
    });
    group.append(
      svg("rect", {
        class: "bill-chart-focus",
        x: x - 4,
        y: 8,
        width: width + 8,
        height: H - 12,
        rx: 9,
        fill: "transparent",
      }),
      svg("rect", {
        x,
        y,
        width,
        height: base - y,
        rx: 5,
        fill: ctx.selected === index ? "url(#bill-bar-active)" : "#d6c7fa",
      }),
      svg(
        "text",
        {
          x: x + width / 2,
          y: Math.max(20, y - 9),
          "text-anchor": "middle",
          fill: ctx.selected === index ? "#6128d0" : "#654b8a",
          "font-size": 10,
          "font-weight": 600,
        },
        `${fmt(value)}${value === null ? "" : ctx.mode === "percent" ? "%" : " h"}`,
      ),
      svg(
        "text",
        {
          x: x + width / 2,
          y: base + 18,
          "text-anchor": "middle",
          fill: ctx.selected === index ? "#5e24ca" : "#9b84bd",
          "font-size": 10,
          "font-weight": ctx.selected === index ? 700 : 400,
        },
        month.short,
      ),
    );
    group.append(
      svg(
        "title",
        {},
        `${month.label}: ${fmt(value, 2)}${ctx.mode === "percent" ? "%" : " h"}`,
      ),
    );
    const choose = () => {
      ctx.selected = index;
      ctx.render();
    };
    group.addEventListener("click", choose);
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        choose();
      }
    });
    root.append(group);
  });
  if (average !== null) {
    const y = base - (average / top) * height;
    root.append(
      svg("line", {
        x1: start,
        x2: W - 8,
        y1: y,
        y2: y,
        stroke: "#be99f6",
        "stroke-dasharray": "4 4",
        "pointer-events": "none",
      }),
    );
  }
  ctx.plot.replaceChildren(root);
  const current = ctx.months[ctx.selected],
    value = values[ctx.selected],
    previous = ctx.selected > 0 ? values[ctx.selected - 1] : null,
    delta = value !== null && previous !== null ? value - previous : null;
  ctx.aside.replaceChildren(
    el("small", { text: current?.label || "Sin meses" }),
    el("strong", {
      text: `${fmt(value, 2)}${value === null || value === undefined ? "" : ctx.mode === "percent" ? "%" : " h"}`,
    }),
    ...(delta === null
      ? []
      : [
          el("span", {
            class: delta < 0 ? "negative" : "positive",
            text: `${delta < 0 ? "↓" : "↑"} ${fmt(Math.abs(delta), 2)} ${ctx.mode === "percent" ? "pp" : "h"}`,
          }),
          el("small", {
            text: `vs. ${ctx.months[ctx.selected - 1].label.toLowerCase()}`,
          }),
        ]),
  );
  ctx.legend.replaceChildren(
    el("span", {
      class: "bill-legend-bars",
      text:
        ctx.mode === "percent" ? "Facturabilidad global" : "Horas facturadas",
    }),
    el("span", {
      class: "bill-legend-average",
      text: `Promedio mensual (${fmt(average)}${average === null ? "" : ctx.mode === "percent" ? "%" : " h"})`,
    }),
  );
}
