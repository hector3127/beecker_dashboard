// @ts-check
import { renderReference } from "./report_table_render_view.js";
// controller: eva4/report_table. Original data, ordering and interactions are preserved.
import { el } from "#app/lib/dom.js";
import { mountTableColumns, cellText } from "../eva/table_columns.js";
import { findAccountLogo, loadAccountLogos } from "#app/lib/account-logos.js";
import { csvCell } from "./report_table_model.js";
import { icon } from "./report_table_view.js";
/**
 * @param {HTMLTableCellElement} cell
 */
export function clientCell(cell) {
  const name = cell.textContent.trim(),
    initials = name
      .split(/\s+/)
      .slice(0, 2)
      .map((word) => word[0])
      .join("");
  const host = el("span", {
    class: "eva4-client-logo",
    "aria-hidden": "true",
    text: initials,
  });
  cell.replaceChildren(
    el("span", { class: "eva4-client-name" }, host, el("span", { text: name })),
  );
  loadAccountLogos().then((items) => {
    const logo = findAccountLogo(items, name);
    if (!logo) return;
    const img = el("img", {
      src: logo.url,
      alt: "",
      loading: "lazy",
      decoding: "async",
    });
    img.addEventListener("error", () => host.replaceChildren(initials), {
      once: true,
    });
    host.replaceChildren(img);
  });
}
/**
 * @param {any} options
 */
export function mountReportTable({
  table,
  rows,
  types,
  kind,
  onCount = () => {},
  totals = null,
}) {
  const section = table.closest("section"),
    heading = section.querySelector("h2"),
    note = section.querySelector(".eva4-note");
  const header = el(
    "div",
    { class: "eva4-section-heading" },
    icon(
      kind === "clients"
        ? "clients"
        : kind === "renewals"
          ? "renew"
          : "database",
    ),
    el("div", {}, heading, ...(note ? [note] : [])),
  );
  section.prepend(header);
  let page = 1,
    size = 10,
    columns,
    wanted = "";
  const count = el("span", {
      id: `${table.id}-count`,
      role: "status",
      "aria-live": "polite",
    }),
    nav = el("nav", {
      "aria-label": `Páginas de ${kind}`,
      class: "eva4-reference-pages",
    });
  const sizes = el(
    "select",
    { "aria-label": `Filas por página de ${kind}` },
    ...[10, 25, 50, 100].map((value) =>
      el("option", { value, text: `${value} / página` }),
    ),
  );
  const footer = el(
    "div",
    { class: "eva4-reference-footer" },
    count,
    nav,
    sizes,
  );
  section.append(footer);
  const normalize = (text) =>
    String(text)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  const filtered = () =>
    columns.sort(
      rows.filter(
        (row) =>
          columns.matches(row) && wanted.split(/\s+/).every(word => normalize(cellText(row)).includes(word)),
      ),
    );
  const unit =
    kind === "processes"
      ? "procesos"
      : kind === "clients"
        ? "clientes"
        : "renovaciones";
  function render() {
    return renderReference({
      get filtered() {
        return filtered;
      },
      get size() {
        return size;
      },
      set size(value) {
        size = value;
      },
      get page() {
        return page;
      },
      set page(value) {
        page = value;
      },
      get table() {
        return table;
      },
      get rows() {
        return rows;
      },
      get totals() {
        return totals;
      },
      get count() {
        return count;
      },
      get unit() {
        return unit;
      },
      get render() {
        return render;
      },
      get kind() {
        return kind;
      },
      get nav() {
        return nav;
      },
      get onCount() {
        return onCount;
      },
    });
  }
  columns = mountTableColumns({
    table,
    rows,
    types,
    onChange: () => {
      page = 1;
      render();
    },
  });
  header.append(
    el("button", {
      type: "button",
      id: `${table.id}-export`,
      class: "eva4-export",
      text: "↓ Exportar",
      title: "Exportar todos los resultados filtrados",
      onclick: () => {
        const heads = [...table.tHead.querySelectorAll("th[data-column-index]")]
          .sort((a, b) => a.dataset.columnIndex - b.dataset.columnIndex)
          .map((th) => th.dataset.columnLabel);
        const text = [
          heads,
          ...filtered().map((row) => [...row.cells].map(cellText)),
        ]
          .map((row) => row.map(csvCell).join(","))
          .join("\r\n");
        const url = URL.createObjectURL(
          new Blob(["\uFEFF" + text], { type: "text/csv;charset=utf-8" }),
        );
        el("a", { href: url, download: `EVA4-${kind}.csv` }).click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      },
    }),
  );
  sizes.addEventListener("change", () => {
    size = Number(sizes.value);
    page = 1;
    render();
  });
  render();
  return {
    filter(text) {
      wanted = normalize(text);
      page = 1;
      return render();
    },
  };
}
export { icon, countryCell } from "./report_table_view.js";
