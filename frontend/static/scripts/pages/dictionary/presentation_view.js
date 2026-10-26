// @ts-check
// view: dictionary/presentation. Original data, ordering and interactions are preserved.
import { svg } from "#app/lib/dom.js";
/** @type {Record<string, string[]>} */
export const PATHS = {
  calendar: ["M4 5h16v16H4zM4 10h16M8 3v4M16 3v4M8 14h2M14 14h2M8 18h2"],
  coins: [
    "M4 6c0 4 16 4 16 0S4 2 4 6ZM4 6v12c0 4 16 4 16 0V6M4 12c0 4 16 4 16 0",
  ],
  file: ["M6 3h8l4 4v14H6V3ZM14 3v5h4M9 12h6M9 16h6"],
  card: ["M3 5h18v14H3zM3 10h18M6 15h5"],
  chart: ["M4 20v-7h3v7ZM10 20V8h3v12ZM16 20V3h3v17Z"],
  money: [
    "M12 5v14M16 8c-6-4-10 3-4 4s4 7-4 4",
    "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  ],
  percent: [
    "M6 18 18 6M8 6a2 2 0 1 0-4 0 2 2 0 0 0 4 0M20 18a2 2 0 1 0-4 0 2 2 0 0 0 4 0",
  ],
  balance: ["M12 3v18M6 21h12M4 7h16M6 7l-4 8h8L6 7ZM18 7l-4 8h8l-4-8Z"],
  tag: ["M3 3h9l9 9-9 9-9-9V3ZM7 7h1"],
  layers: ["m3 7 9-5 9 5-9 5-9-5ZM3 12l9 5 9-5M3 17l9 5 9-5"],
  clock: ["M12 6v6h5", "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0"],
  flag: ["M5 22V3l14 1v9L5 12"],
  target: [
    "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
    "M18 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0",
    "M14 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0",
  ],
};
/**
 * @param {string} name
 */
export function dictionaryIcon(name) {
  return svg(
    "svg",
    {
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "1.8",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
      "aria-hidden": "true",
    },
    ...(PATHS[name] || PATHS.file).map((d) => svg("path", { d })),
  );
}
