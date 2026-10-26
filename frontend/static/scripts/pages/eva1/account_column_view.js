// @ts-check
import { el } from "#app/lib/dom.js";

/** @param {HTMLTableRowElement} row @param {string} name @param {string} initials */
export function insertAccountCell(row, name, initials) {
  const host = el("span", {
    class: "eva1-account-logo",
    "aria-hidden": "true",
    text: initials,
  });
  row.cells[0].after(
    el(
      "td",
      {},
      el(
        "span",
        { class: "eva1-account" },
        host,
        el("span", { text: name || "Sin cuenta" }),
      ),
    ),
  );
  return host;
}

/** @param {HTMLElement} host @param {string} url @param {string} initials */
export function showAccountLogo(host, url, initials) {
  const image = el("img", {
    src: url,
    alt: "",
    width: 26,
    height: 26,
    loading: "lazy",
    decoding: "async",
  });
  image.addEventListener("error", () => host.replaceChildren(initials), {
    once: true,
  });
  host.replaceChildren(image);
}
