// @ts-check
import { renderReference } from "./history_table_render_view.js";
// controller: eva1/history_table. Original data, ordering and interactions are preserved.
import { mountAccountColumn } from "./account_column.js";
import { el } from "#app/lib/dom.js";
import { mountTableColumns, cellText } from "../eva/table_columns.js";
import { csvCell } from "./history_table_model.js";
/**
 * @param {HTMLElement} body
 */
export function mountIxbHistory(body) {
  const table = body.querySelector("table");
  if (!table) return;
  const rows = [...table.querySelectorAll("tbody tr[data-manager]")];
  mountAccountColumn(table, rows);
  let page = 1,
    size = 10,
    columns;
  const footer = body.querySelector(".table-bottom");
  const count = el("span", {
    id: "eva-history-count",
    role: "status",
    "aria-live": "polite",
  });
  const pages = el("nav", {
    class: "eva-history-pages",
    "aria-label": "Páginas del histórico IXB",
  });
  const bottom = footer || el("div", { class: "table-bottom" });
  bottom.classList.add("eva-history-footer");
  const sizes = el(
    "select",
    {
      class: "eva-history-size",
      id: "eva-history-size",
      "aria-label": "Proyectos por página del histórico IXB",
    },
    ...[10, 25, 50, 100].map((value) => el("option", { value, text: value })),
  );
  bottom.replaceChildren(count, pages, sizes);
  if (!footer) body.append(bottom);
  const results = () => columns.sort(rows.filter(columns.matches));
  const empty = el(
    "tr",
    { class: "eva-history-empty" },
    el("td", {
      colspan: 26,
      class: "vacio",
      text: "No hay proyectos que coincidan con los filtros.",
    }),
  );
  function render() {
    return renderReference({
      get results() {
        return results;
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
      get empty() {
        return empty;
      },
      get count() {
        return count;
      },
      get render() {
        return render;
      },
      get pages() {
        return pages;
      },
    });
  }
  columns = mountTableColumns({
    table,
    rows,
    types: Object.fromEntries(
      Array.from({ length: 26 }, (_, index) => [
        index,
        [6, 7].includes(index) ? "date" : index >= 8 ? "number" : "text",
      ]),
    ),
    onChange: () => {
      page = 1;
      render();
    },
  });
  const summary = body.closest("details").querySelector("summary");
  summary.append(
    el("button", {
      id: "eva-history-export",
      type: "button",
      class: "eva-btn eva-history-export",
      text: "↓ Exportar",
      title: "Exportar todos los proyectos históricos filtrados",
      onclick: (event) => {
        event.preventDefault();
        event.stopPropagation();
        const headers = [
          ...table.tHead.querySelectorAll("th[data-column-index]"),
        ]
          .sort(
            (a, b) =>
              Number(a.dataset.columnIndex) - Number(b.dataset.columnIndex),
          )
          .map((th) => th.dataset.columnLabel);
        const content = [
          headers,
          ...results().map((row) => [...row.cells].map(cellText)),
        ]
          .map((row) => row.map(csvCell).join(","))
          .join("\r\n");
        const url = URL.createObjectURL(
          new Blob(["\uFEFF" + content], { type: "text/csv;charset=utf-8" }),
        );
        el("a", {
          href: url,
          download: "EVA1-historico-IXB-RaaS-SaaS.csv",
        }).click();
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
}
