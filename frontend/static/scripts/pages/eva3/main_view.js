// @ts-check
import { el } from "#app/lib/dom.js";
import { fmt } from "./model.js";

/** @param {HTMLElement} cell @param {number} value @param {boolean} bad @param {string} suffix */
/**
 * @param {HTMLTableCellElement} cell
 * @param {any} value
 * @param {boolean} bad
 * @param {string} suffix
 */
export function badge(cell, value, bad, suffix = "") {
  cell.replaceChildren(
    el("span", {
      class: "bd " + (bad ? "bad" : "ok"),
      text: fmt(value) + suffix,
    }),
  );
}
