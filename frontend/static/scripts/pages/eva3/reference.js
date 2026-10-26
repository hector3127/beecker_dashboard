// @ts-check
import { renderReference } from "./reference_render_view.js";
// controller: eva3/reference. Original data, ordering and interactions are preserved.
import { mountTableColumns } from "../eva/table_columns.js";
import { el, svg } from "#app/lib/dom.js";
import { findAccountLogo, loadAccountLogos } from "#app/lib/account-logos.js";
import { download } from "./reference_view.js";
export function mountReference() {
  const table = document.querySelector("table.w");
  if (!table) return;
  table.id = "eva3-projects";
  const card = table.closest("section");
  card.classList.add("eva3-project-card");
  const summaryTable = document.querySelector(".evi-617963 table");
  const summaryCard = summaryTable.closest("section");
  summaryCard.classList.add("eva3-summary");
  const wrap = el("div", { class: "eva3-summary-scroll" });
  summaryTable.before(wrap);
  wrap.append(summaryTable);
  const rows = [...table.querySelectorAll("tbody tr[data-project]")];
  const records = rows.map((row) => ({
    row,
    manager: row.cells[0].textContent.trim(),
    account: row.cells[1].textContent.trim(),
    service: row.cells[3].textContent.trim(),
  }));
  const tabs = el("div", {
    class: "eva3-tabs",
    role: "group",
    "aria-label": "Proyectos por servicio",
  });
  let tab = "",
    page = 1,
    size = 25,
    columns;
  const count = el("span", {
    id: "eva3-count",
    role: "status",
    "aria-live": "polite",
  });
  const pagination = el("nav", {
    class: "eva3-pagination",
    "aria-label": "Páginas de proyectos",
  });
  const pageSize = el(
    "select",
    { id: "eva3-page-size", "aria-label": "Proyectos por página" },
    ...[15, 25, 50, 100].map((value) => el("option", { value, text: value })),
  );
  pageSize.value = "25";
  const footer = el(
    "div",
    { class: "eva3-table-footer" },
    count,
    pagination,
    pageSize,
  );
  table.parentElement.before(tabs);
  card.append(footer);
  function matched() {
    const result = records.filter(
      (record) =>
        (!columns || columns.matches(record.row)) &&
        (!tab || record.service === tab),
    );
    return columns
      ? columns
          .sort(result.map((record) => record.row))
          .map((row) => records.find((record) => record.row === row))
      : result;
  }
  function render() {
    return renderReference({
      get matched() {
        return matched;
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
      get rows() {
        return rows;
      },
      get count() {
        return count;
      },
      get pagination() {
        return pagination;
      },
      get render() {
        return render;
      },
      get tabs() {
        return tabs;
      },
      get tab() {
        return tab;
      },
      set tab(value) {
        tab = value;
      },
    });
  }
  ["", "AER", "T&M"].forEach((value) =>
    tabs.append(
      el("button", {
        type: "button",
        dataset: { service: value },
        text: `${value || "Todos"} (${records.filter((record) => !value || record.service === value).length})`,
        onclick: () => {
          tab = value;
          page = 1;
          render();
        },
      }),
    ),
  );
  pageSize.addEventListener("change", () => {
    size = Number(pageSize.value);
    page = 1;
    render();
  });
  const exportButton = el("button", {
    id: "eva3-export",
    class: "eva3-export",
    type: "button",
    text: "↥ Exportar",
    onclick: () =>
      download("EVA3-proyectos.csv", [
        [...table.tHead.rows[0].cells]
          .slice(0, 13)
          .map((cell) => cell.textContent.trim()),
        ...matched().map((record) =>
          [...record.row.cells]
            .slice(0, 13)
            .map((cell, index) =>
              index === 1 ? record.account : cell.textContent.trim(),
            ),
        ),
      ]),
  });
  card.querySelector(".section-title").append(exportButton);
  summaryCard.querySelector(".section-title").append(
    el("button", {
      id: "eva3-summary-export",
      class: "eva3-export",
      type: "button",
      text: "↥ Exportar",
      onclick: () =>
        download(
          "EVA3-personas-por-DM.csv",
          [...summaryTable.rows].map((row) =>
            [...row.cells].map((cell) => cell.textContent.trim()),
          ),
        ),
    }),
  );
  table.tHead.rows[0].cells[1].textContent = "Cuenta";
  table.tHead.rows[0].append(
    el("th", { scope: "col", "aria-label": "Ver proyecto" }),
  );
  records.forEach((record) => {
    const initials = record.account
      .split(/\s+/)
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase();
    const logo = el("span", {
      class: "eva3-account-logo",
      "aria-hidden": "true",
      text: initials || "—",
    });
    record.logo = logo;
    record.row.cells[0].title = record.manager;
    record.row.cells[1].replaceChildren(
      el(
        "span",
        { class: "eva3-account" },
        logo,
        el("span", { text: record.account || "Sin cuenta" }),
      ),
    );
    record.row.cells[3].replaceChildren(
      el("span", {
        class: `eva3-service service-${record.service === "AER" ? "aer" : "tym"}`,
        text: record.service,
      }),
    );
    const projectLink = record.row.cells[2].querySelector("a");
    record.row.append(
      el(
        "td",
        {},
        el("a", {
          class: "eva3-row-link",
          href: projectLink.href,
          "aria-label": `Ver proyecto ${record.row.dataset.project}`,
          text: "↗",
        }),
      ),
    );
  });
  loadAccountLogos().then((items) => {
    for (const record of records) {
      const logo = findAccountLogo(items, record.account);
      if (!logo) continue;
      const image = el("img", {
        src: logo.url,
        alt: "",
        loading: "lazy",
        decoding: "async",
      });
      image.addEventListener("error", () => image.remove(), { once: true });
      image.addEventListener("load", () => record.logo.replaceChildren(image), {
        once: true,
      });
      image.loading = "eager";
    }
  });
  const history = document.getElementById("eva3-closed-box").closest("section");
  const note = document.querySelector(".note");
  if (note) note.before(history);
  const summary = history.querySelector("summary");
  summary.append(
    el("span", {
      class: "eva3-history-arrow",
      "aria-hidden": "true",
      text: "›",
    }),
  );
  const hero = document.querySelector(".pgh");
  const art = svg(
    "svg",
    { class: "eva3-hero-art", viewBox: "0 0 330 140", "aria-hidden": "true" },
    svg(
      "defs",
      {},
      svg(
        "linearGradient",
        { id: "eva3-folder-gradient", x2: "1", y2: "1" },
        svg("stop", { offset: "0", "stop-color": "#eee6ff" }),
        svg("stop", { offset: "1", "stop-color": "#8c64ed" }),
      ),
    ),
    ...[0, 1, 2].map((index) =>
      svg("path", {
        d: "M45 42V25Q45 16 54 16H105L122 30H245Q254 30 254 40V125H45Z",
        fill: "url(#eva3-folder-gradient)",
        stroke: "#ffffff66",
        "stroke-width": "2",
        transform: `translate(${index * 17} ${index * -4}) rotate(-12 150 80)`,
      }),
    ),
    ...[28, 48, 70, 96].map((height, index) =>
      svg("rect", {
        x: 195 + index * 23,
        y: 135 - height,
        width: 15,
        height,
        rx: 3,
        fill: "#dcd0ff",
        stroke: "#ffffff88",
      }),
    ),
    svg("path", {
      d: "M168 111Q235 90 293 30M270 30H293V54",
      fill: "none",
      stroke: "#fff",
      "stroke-width": "7",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    }),
  );
  hero.append(art);
  columns = mountTableColumns({
    table,
    rows,
    types: Object.fromEntries(
      Array.from({ length: 13 }, (_, index) => [
        index,
        [6, 7].includes(index)
          ? "date"
          : index === 4 || index >= 8
            ? "number"
            : "text",
      ]),
    ),
    exclude: [13],
    onChange: () => {
      page = 1;
      render();
    },
  });
  table.addEventListener("eva3-active-updated", () => columns.refresh());
  render();
}
