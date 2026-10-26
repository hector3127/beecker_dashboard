// @ts-check
// Cuenta de origen y logo guardado, sin modificar la identidad del proyecto.
import { el } from "#app/lib/dom.js";
import { findAccountLogo, loadAccountLogos } from "#app/lib/account-logos.js";
import { accountInitials } from "./account_column_model.js";
import { insertAccountCell, showAccountLogo } from "./account_column_view.js";
/**
 * @param {HTMLTableElement} table
 * @param {HTMLTableRowElement[]} rows
 */
export function mountAccountColumn(table, rows) {
  const first = table.tHead.rows[0].cells[0];
  first.after(
    el("th", { scope: "col", rowspan: first.rowSpan, text: "Cuenta" }),
  );
  const logos = loadAccountLogos();
  rows.forEach((row) => {
    const name = row.dataset.client || "",
      initials = accountInitials(name);
    const host = insertAccountCell(row, name, initials);
    logos.then((items) => {
      const logo = findAccountLogo(items, name);
      if (!logo) return;
      showAccountLogo(host, logo.url, initials);
    });
  });
}
