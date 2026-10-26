// @ts-check
import { renderReference } from "./history_reference_render_view.js";
// controller: eva3/history_reference. Original data, ordering and interactions are preserved.
import { el } from "#app/lib/dom.js";
import { findAccountLogo, loadAccountLogos } from "#app/lib/account-logos.js";
import { columnColor, matchesColumn, openColumnMenu } from "./column_menu.js";
import { dateValue, csvCell, status } from "./history_reference_model.js";
import { text } from "./history_reference_view.js";
/**
 * @param {HTMLElement} body
 */
export function mountHistoryReference(body) {
  const table = body.querySelector("table");
  if (!table || body.querySelector(".eva3-history-footer")) return;
  table.id = "eva3-history-table";
  table.classList.add("eva3-history-table");
  const rows = [...table.querySelectorAll("tbody tr[data-closed-id]")];
  const records = rows.map((row) => ({
    row,
    manager: text(row.cells[0]),
    id: row.dataset.closedId,
    service: text(row.cells[2]),
    name: text(row.cells[3]),
    status: status(text(row.cells[4])),
    start: dateValue(text(row.cells[5])),
    finish: dateValue(text(row.cells[6])),
    client: row.dataset.closedClient || "",
  }));
  table.tHead.rows[0].cells[0].after(
    el("th", { scope: "col", text: "Cuenta" }),
  );
  const logos = loadAccountLogos();
  records.forEach((record) => {
    const initials =
      record.client
        .trim()
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => word[0])
        .join("")
        .toUpperCase() || "—";
    const host = el("span", {
      class: "eva3-account-logo",
      "aria-hidden": "true",
      text: initials,
    });
    record.row.cells[0].after(
      el(
        "td",
        {},
        el(
          "span",
          { class: "eva3-account" },
          host,
          el("span", { text: record.client || "Sin cuenta" }),
        ),
      ),
    );
    logos.then((items) => {
      const logo = findAccountLogo(items, record.client);
      if (!logo) return;
      const image = el("img", {
        src: logo.url,
        alt: "",
        loading: "lazy",
        decoding: "async",
      });
      image.addEventListener("error", () => host.replaceChildren(initials), {
        once: true,
      });
      host.replaceChildren(image);
    });
  });
  const clear = el("button", {
    id: "eva3-history-clear",
    type: "button",
    text: "Limpiar filtros",
    class: "eva3-history-clear",
  });
  const filters = new Map();
  const count = el("span", {
    id: "eva3-history-count",
    role: "status",
    "aria-live": "polite",
  });
  const pages = el("nav", {
    class: "eva3-history-pages",
    "aria-label": "Páginas del histórico",
  });
  const sizeSelect = el(
    "select",
    {
      id: "eva3-history-size",
      "aria-label": "Proyectos históricos por página",
    },
    ...[12, 25, 50, 100].map((size) =>
      el("option", { value: size, text: `${size} / página` }),
    ),
  );
  body.append(
    el(
      "div",
      { class: "eva3-history-footer" },
      count,
      clear,
      pages,
      sizeSelect,
    ),
  );
  let page = 1,
    size = 12,
    sortIndex = null,
    direction = 1,
    sortColor = null;
  function numeric(cell) {
    const value = text(cell).replace(/[,\s%]/g, "");
    return /^-?\d+(\.\d+)?$/.test(value) ? Number(value) : null;
  }
  function value(record, index) {
    return index >= 8
      ? numeric(record.row.cells[index])
      : index === 6
        ? record.start || null
        : index === 7
          ? record.finish || null
          : index === 5
            ? record.status
            : text(record.row.cells[index]);
  }
  function filtered() {
    const result = records.filter((record) =>
      [...filters].every(([index, filter]) =>
        matchesColumn(
          text(record.row.cells[index]),
          value(record, index),
          columnColor(record.row.cells[index]).key,
          filter,
        ),
      ),
    );
    if (sortIndex !== null)
      result.sort((a, b) => {
        if (sortColor) {
          const order =
            Number(columnColor(b.row.cells[sortIndex]).key === sortColor) -
            Number(columnColor(a.row.cells[sortIndex]).key === sortColor);
          if (order) return order;
        }
        const av = value(a, sortIndex),
          bv = value(b, sortIndex);
        if (av === null) return bv === null ? 0 : 1;
        if (bv === null) return -1;
        return (
          direction *
          (typeof av === "number"
            ? av - bv
            : String(av).localeCompare(String(bv), "es", { numeric: true }))
        );
      });
    return result;
  }
  const empty = el(
    "tr",
    { class: "eva3-history-empty" },
    el("td", {
      colspan: 12,
      text: "Sin proyectos que coincidan con los filtros.",
    }),
  );
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
      get records() {
        return records;
      },
      get empty() {
        return empty;
      },
      get count() {
        return count;
      },
      get sortIndex() {
        return sortIndex;
      },
      set sortIndex(value) {
        sortIndex = value;
      },
      get direction() {
        return direction;
      },
      set direction(value) {
        direction = value;
      },
      get filters() {
        return filters;
      },
      get render() {
        return render;
      },
      get pages() {
        return pages;
      },
    });
  }
  records.forEach((record) => {
    record.row.cells[3].replaceChildren(
      el("span", {
        class: `eva3-service service-${record.service === "AER" ? "aer" : "tym"}`,
        text: record.service,
      }),
    );
    record.row.cells[5].replaceChildren(
      el("span", {
        class: `eva3-history-status ${record.status === "Finalizado" ? "finished" : record.status === "Cancelado" ? "cancelled" : "unknown"}`,
        text: record.status,
      }),
    );
  });
  table.querySelectorAll("thead th").forEach((th, index) => {
    const label = th.textContent;
    th.dataset.label = label;
    th.setAttribute("scope", "col");
    const trigger = el(
      "button",
      {
        type: "button",
        "aria-expanded": "false",
        "aria-haspopup": "dialog",
        onclick: () =>
          openColumnMenu({
            host: body,
            trigger,
            label,
            type:
              index >= 8
                ? "number"
                : index === 6 || index === 7
                  ? "date"
                  : "text",
            entries: records.map((record) => ({
              raw: text(record.row.cells[index]),
              color: columnColor(record.row.cells[index]),
            })),
            filter: filters.get(index),
            onApply: (filter) => {
              if (filter.values || filter.color || filter.condition)
                filters.set(index, filter);
              else filters.delete(index);
              page = 1;
              render();
            },
            onSort: (order, color) => {
              sortIndex = index;
              direction = order;
              sortColor = color;
              page = 1;
              render();
            },
          }),
      },
      el("span", { text: label }),
      el("span", {
        "aria-hidden": "true",
        class: "eva3-column-chevron",
        text: " ▾",
      }),
    );
    th.replaceChildren(trigger);
  });
  sizeSelect.addEventListener("change", () => {
    size = Number(sizeSelect.value);
    page = 1;
    render();
  });
  clear.addEventListener("click", () => {
    filters.clear();
    page = 1;
    render();
  });
  body.addEventListener("eva3-history-updated", render);
  const summary = body.closest("details").querySelector("summary");
  const exportButton = el("button", {
    id: "eva3-history-export",
    class: "eva3-export",
    type: "button",
    text: "↓ Exportar",
    title: "Descargar todos los proyectos históricos filtrados",
    onclick: (event) => {
      event.preventDefault();
      event.stopPropagation();
      const content = [
        [...table.tHead.rows[0].cells].map((th) => th.dataset.label),
        ...filtered().map((record) => [...record.row.cells].map(text)),
      ]
        .map((row) => row.map(csvCell).join(","))
        .join("\r\n");
      const url = URL.createObjectURL(
        new Blob(["\uFEFF" + content], { type: "text/csv;charset=utf-8" }),
      );
      el("a", { href: url, download: "EVA3-historico-AER-TYM.csv" }).click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  });
  summary.querySelector("#eva3-history-export")?.remove();
  summary.append(exportButton);
  render();
}
