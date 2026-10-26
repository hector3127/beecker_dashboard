// @ts-check
// view: eva4/report_table. Original data, ordering and interactions are preserved.
import { el, svg } from "#app/lib/dom.js";
/**
 * @param {string} name
 */
export function icon(name) {
  const paths = {
    gear: "m9 2-.5 3-2 1-2.8-1L1.5 9l2.5 2v2l-2.5 2 2.2 3.7L6.5 18l2 1 .5 3h5l.5-3 2-1 2.8.7 2.2-3.7-2.5-2v-2l2.5-2-2.2-3.7-2.8 1-2-1L14 2ZM16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
    layers: "m3 7 9-4 9 4-9 4zM3 12l9 4 9-4M3 17l9 4 9-4",
    play: "m10 8 6 4-6 4zM21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0",
    pause: "M9 8v8M15 8v8M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0",
    renew: "M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5M4 16a8 8 0 0 0 14 3l3-3m0 5v-5h-5",
    clients:
      "M4 21V4h10v17M14 9h6v12M7 7h4M7 11h4M7 15h4M7 19h4M17 12v2M17 17v2",
    database:
      "M4 5c0-4 16-4 16 0s-16 4-16 0v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0",
  };
  return el(
    "span",
    { class: `eva4-reference-icon icon-${name}` },
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
      svg("path", { d: paths[name] || paths.layers }),
    ),
  );
}
/**
 * @param {HTMLTableCellElement} cell
 */
export function countryCell(cell) {
  const name = cell.textContent.trim(),
    code = {
      MEX: "MX",
      MX: "MX",
      USA: "US",
      US: "US",
      GTM: "GT",
      GT: "GT",
      COL: "CO",
      CO: "CO",
      ECU: "EC",
      EC: "EC",
      CHL: "CL",
      CL: "CL",
      BRA: "BR",
      BR: "BR",
    }[name];
  if (!code) return;
  const flag = svg("svg", {
      viewBox: "0 0 24 16",
      width: 21,
      height: 14,
      class: "eva4-country-flag",
      "aria-hidden": "true",
    }),
    rect = (x, y, width, height, fill) =>
      svg("rect", { x, y, width, height, fill });
  if (code === "MX" || code === "GT") {
    flag.append(
      rect(0, 0, 8, 16, code === "MX" ? "#098050" : "#51b6df"),
      rect(8, 0, 8, 16, "#fff"),
      rect(16, 0, 8, 16, code === "MX" ? "#d82f37" : "#51b6df"),
      svg("circle", { cx: 12, cy: 8, r: 1.4, fill: "#b59642" }),
    );
  }
  if (code === "CO" || code === "EC")
    flag.append(
      rect(0, 0, 24, 8, "#f7d435"),
      rect(0, 8, 24, 4, "#2547a2"),
      rect(0, 12, 24, 4, "#cf3341"),
    );
  if (code === "CL")
    flag.append(
      rect(0, 0, 24, 8, "#fff"),
      rect(0, 8, 24, 8, "#da3441"),
      rect(0, 0, 8, 8, "#234c9c"),
      svg("path", { d: "m4 1 1 2h2L5 4l1 2-2-1-2 1 1-2-2-1h2z", fill: "#fff" }),
    );
  if (code === "BR")
    flag.append(
      rect(0, 0, 24, 16, "#19904c"),
      svg("path", { d: "M12 1 23 8 12 15 1 8Z", fill: "#f7d63b" }),
      svg("circle", { cx: 12, cy: 8, r: 4, fill: "#2458a4" }),
    );
  if (code === "US") {
    flag.append(
      rect(0, 0, 24, 16, "#fff"),
      ...Array.from({ length: 7 }, (_, i) =>
        rect(0, (i * 16) / 6.5, 24, 16 / 13, "#c83d4b"),
      ),
      rect(0, 0, 10, 9, "#29487d"),
      ...Array.from({ length: 9 }, (_, i) =>
        svg("circle", {
          cx: 2 + (i % 3) * 3,
          cy: 2 + Math.floor(i / 3) * 2.5,
          r: 0.45,
          fill: "#fff",
        }),
      ),
    );
  }
  cell.replaceChildren(flag, " ", name);
}
