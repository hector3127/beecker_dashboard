// @ts-check
// Cumplimiento (C) por mes de cada Delivery Manager: gráfica con leyenda que
// resalta una serie y escala ampliada o completa.
import { el, svg } from "#app/lib/dom.js";
import { trendPath } from "./trend_model.js";

const COLORS = [
  "#6347ed",
  "#18ad78",
  "#ed9c0a",
  "#e0457b",
  "#2a9fd6",
  "#8a7eae",
];
const LEFT = 45;
const RIGHT = 535;
const TOP = 16;
const BOTTOM = 234;
/** @param {unknown} v */
const valid = (v) => typeof v === "number" && Number.isFinite(v);

/**
 * @param {{labels: string[], series: {name: string, values: (number | null)[]}[], highlight?: string[]}} data
 * @returns {HTMLElement[]} Herramientas, grafica, leyenda y nota; ya con su comportamiento.
 */
export function renderChart(data) {
  const chart = svg("svg", {
    id: "kpi-chart",
    viewBox: "0 0 560 270",
    role: "img",
    "aria-label":
      "Tendencia mensual de cumplimiento en costo por Delivery Manager",
  });
  const legend = el("div", { id: "kpi-legend", class: "kpi-legend" });
  const toggle = /** @type {HTMLButtonElement} */ (
    el("button", {
      id: "kpi-chart-toggle",
      type: "button",
      "aria-pressed": "false",
    })
  );
  const scale = el("span", { id: "kpi-chart-scale", role: "status" });
  const count = data.labels.length;
  const step = count > 1 ? (RIGHT - LEFT) / (count - 1) : 0;
  const x = (/** @type {number} */ i) =>
    count > 1 ? LEFT + i * step : (LEFT + RIGHT) / 2;
  let completeScale = false;
  /** @type {number | null} */
  let selected = null;

  /** @param {string} tag @param {Record<string, string | number>} attrs @param {string} [text] */
  const node = (tag, attrs, text) => {
    const child = svg(tag, attrs, ...(text === undefined ? [] : [text]));
    chart.appendChild(child);
    return child;
  };

  function draw() {
    chart.replaceChildren();
    const series = data.series.filter(
      (_, i) => selected === null || selected === i,
    );
    const values = /** @type {number[]} */ (
      series.flatMap((s) => s.values).filter(valid)
    );
    const low = values.length ? Math.min(...values) : 0;
    const high = values.length ? Math.max(...values) : 100;
    const minimum = completeScale
      ? Math.min(0, Math.floor(low / 10) * 10)
      : low >= 0
        ? Math.max(0, Math.floor((low - 5) / 10) * 10)
        : Math.floor((low - 5) / 10) * 10;
    const maximum = completeScale
      ? Math.max(100, Math.ceil(high / 10) * 10)
      : Math.max(minimum + 10, Math.ceil((high + 5) / 10) * 10);
    const y = (/** @type {number} */ v) =>
      BOTTOM - ((v - minimum) / (maximum - minimum)) * (BOTTOM - TOP);
    scale.textContent = `${completeScale ? "Escala completa: " : "Escala ampliada: "}${minimum}–${maximum}%`;
    toggle.textContent = completeScale
      ? "Ampliar diferencias"
      : "Ver escala completa";
    toggle.setAttribute("aria-pressed", String(completeScale));
    const interval =
      completeScale && minimum === 0 && maximum === 100
        ? 25
        : maximum - minimum <= 20
          ? 5
          : Math.ceil((maximum - minimum) / 5 / 10) * 10;
    const ticks = [];
    for (let value = minimum; value <= maximum; value += interval)
      ticks.push(value);
    if (ticks[ticks.length - 1] !== maximum) ticks.push(maximum);
    for (const value of ticks) {
      node("line", {
        x1: LEFT,
        x2: RIGHT,
        y1: y(value),
        y2: y(value),
        stroke: "#e4def4",
        "stroke-dasharray": "3 4",
      });
      node(
        "text",
        {
          x: LEFT - 7,
          y: y(value) + 4,
          "text-anchor": "end",
          fill: "#8a7eae",
          "font-size": 10,
        },
        `${value}%`,
      );
    }
    data.labels.forEach((label, i) => {
      if ((data.highlight || []).includes(label)) {
        const width = count > 1 ? step : 80;
        const start = Math.max(LEFT, x(i) - width / 2);
        node("rect", {
          x: start,
          y: TOP,
          width: Math.min(RIGHT, x(i) + width / 2) - start,
          height: BOTTOM - TOP,
          fill: "#6347ed",
          "fill-opacity": 0.07,
          rx: 4,
        });
      }
      node(
        "text",
        {
          x: x(i),
          y: 256,
          "text-anchor": "middle",
          fill: "#8a7eae",
          "font-size": 11,
        },
        label,
      );
    });
    data.series.forEach((serie, index) => {
      if (selected !== null && selected !== index) return;
      const color = COLORS[index % COLORS.length];
      const path = trendPath(
        serie.values.map((value, i) =>
          valid(value)
            ? { x: x(i), y: y(/** @type {number} */ (value)) }
            : null,
        ),
      );
      node("path", {
        d: path,
        fill: "none",
        stroke: color,
        "stroke-width": 2.5,
        "stroke-linejoin": "round",
      });
      serie.values.forEach((value, i) => {
        if (!valid(value)) return;
        const point = node("circle", {
          cx: x(i),
          cy: y(/** @type {number} */ (value)),
          r: 3.5,
          fill: color,
        });
        point.appendChild(
          svg("title", {}, `${serie.name} · ${data.labels[i]}: ${value}%`),
        );
      });
    });
    if (!values.length)
      node(
        "text",
        { x: 290, y: 125, "text-anchor": "middle", fill: "#8075a7" },
        "Sin valores para este periodo",
      );
    [...legend.children].forEach((button, i) => {
      button.setAttribute("aria-pressed", String(selected === i));
      /** @type {HTMLElement} */ (button).style.opacity =
        selected === null || selected === i ? "1" : ".5";
    });
  }

  data.series.forEach((serie, index) => {
    const dot = el("i", { "aria-hidden": "true" });
    dot.style.background = COLORS[index % COLORS.length];
    legend.append(
      el(
        "button",
        {
          type: "button",
          onclick: () => {
            selected = selected === index ? null : index;
            draw();
          },
        },
        dot,
        serie.name,
      ),
    );
  });
  toggle.addEventListener("click", () => {
    completeScale = !completeScale;
    draw();
  });
  draw();
  return [
    el("div", { class: "kpi-chart-tools" }, scale, toggle),
    chart,
    legend,
    el("p", {
      class: "note",
      text: "Selecciona un DM para ver su tendencia; pulsa otra vez para comparar todos. Los puntos son valores mensuales reales; las curvas suavizan el trazado. Los meses sin dato quedan separados.",
    }),
  ];
}
