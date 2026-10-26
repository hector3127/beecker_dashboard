// @ts-check
// view: billability/reference. Original data, ordering and interactions are preserved.
import { el, svg } from "#app/lib/dom.js";
/**
 * @param {string} kind
 */
export function icon(kind) {
  const paths = {
    bars: "M5 20V12M12 20V4M19 20V9",
    file: "M5 2h9l5 5v15H5zM14 2v6h5M8 12h8M8 16h6",
    globe: "M3 12h18M12 3c-6 4-6 14 0 18M12 3c6 4 6 14 0 18",
  };
  return el(
    "span",
    { class: "bill-reference-icon" },
    svg(
      "svg",
      {
        viewBox: "0 0 24 24",
        fill: "none",
        stroke: "currentColor",
        "stroke-width": 1.8,
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
        "aria-hidden": "true",
      },
      ...(kind === "globe" ? [svg("circle", { cx: 12, cy: 12, r: 9 })] : []),
      svg("path", { d: paths[kind] }),
    ),
  );
}
/**
 * @param {(number|null)[]} values
 * @param {number} index
 */
export function sparkline(values, index) {
  const present = values.filter((value) => value !== null);
  if (!present.length) return null;
  const min = Math.min(...present),
    max = Math.max(...present);
  const points = values
    .map((value, i) =>
      value === null
        ? null
        : [
            (i * 140) / Math.max(values.length - 1, 1),
            57 - ((value - min) / Math.max(max - min, 1)) * 45,
          ],
    )
    .filter(Boolean);
  if (!points.length) return null;
  const d = points
    .map((point, i) => `${i ? "L" : "M"}${point[0]},${point[1]}`)
    .join(" ");
  const last = points.at(-1);
  return svg(
    "svg",
    { class: "bill-sparkline", viewBox: "0 0 145 66", "aria-hidden": "true" },
    svg(
      "defs",
      {},
      svg(
        "linearGradient",
        { id: `bill-spark-${index}`, x2: 0, y2: 1 },
        svg("stop", {
          offset: "0%",
          "stop-color": "currentColor",
          "stop-opacity": ".3",
        }),
        svg("stop", {
          offset: "100%",
          "stop-color": "currentColor",
          "stop-opacity": "0",
        }),
      ),
    ),
    svg("path", {
      d: `${d} L${last[0]},66 L${points[0][0]},66Z`,
      fill: `url(#bill-spark-${index})`,
    }),
    svg("path", {
      d,
      fill: "none",
      stroke: "currentColor",
      "stroke-width": 2,
      "stroke-linejoin": "round",
    }),
    svg("circle", {
      cx: last[0],
      cy: last[1],
      r: 3.5,
      fill: "currentColor",
      stroke: "#fff",
      "stroke-width": 2,
    }),
  );
}
