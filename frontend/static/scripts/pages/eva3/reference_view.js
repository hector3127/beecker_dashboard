// @ts-check
// view: eva3/reference. Original data, ordering and interactions are preserved.
import { el } from "#app/lib/dom.js";
import { csvCell } from "./reference_model.js";
/**
 * @param {string} name
 * @param {HTMLTableRowElement[]} rows
 */
export function download(name, rows) {
  const url = URL.createObjectURL(
    new Blob(
      ["\uFEFF" + rows.map((row) => row.map(csvCell).join(",")).join("\r\n")],
      { type: "text/csv;charset=utf-8" },
    ),
  );
  el("a", { href: url, download: name }).click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
