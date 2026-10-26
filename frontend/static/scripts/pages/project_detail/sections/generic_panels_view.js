import { el } from "#app/lib/dom.js";
import { resourcesModel, milestonesModel } from "./generic_panels_model.js";

export function resourcePanel(data) {
  const model = resourcesModel(data);
  const titles = [
    "Rol",
    "Recurso",
    "Banda",
    "Costing Rate",
    "Hrs Estimadas",
    "Hrs Reales",
    "Hrs No FACT",
    "Balance",
    "% Cumpl.",
    "Costo Real",
    "Estado",
  ];
  return el(
    "div",
    { class: "card gp-resources", id: "card-carga-trabajo-recurso" },
    el(
      "div",
      { class: "gp-resource-head" },
      el("h3", { class: "gp-resource-title" }, "CARGA DE TRABAJO POR RECURSO"),
      el("span", { id: "rango-clockify-dashboard", class: "gp-range" }),
    ),
    el(
      "div",
      { class: "gp-table-scroll" },
      el(
        "table",
        { class: "data-table" },
        el(
          "thead",
          {},
          el("tr", {}, ...titles.map((title) => el("th", {}, title))),
        ),
        el(
          "tbody",
          {},
          ...model.rows.map((row) =>
            el(
              "tr",
              {},
              ...row.cells.map((cell) => el("td", {}, cell)),
              el(
                "td",
                {},
                el("span", { class: "badge " + row.badge }, row.state),
              ),
            ),
          ),
        ),
        el(
          "tfoot",
          {},
          el(
            "tr",
            { class: "gp-total" },
            el("td", { colspan: 4 }, "Totales del proyecto"),
            ...model.totals.map((cell) => el("td", {}, cell)),
          ),
        ),
      ),
    ),
  );
}

const icons = { complete: "✅", running: "🚀", suspended: "⏸️", pending: "🚩" };
export function milestonePanel(rows) {
  const fragment = document.createDocumentFragment();
  const model = milestonesModel(rows);
  if (!rows.length) {
    fragment.append(
      el("div", { class: "gp-empty" }, "Sin hitos registrados aún."),
    );
    return fragment;
  }
  for (const [title, items, completed] of [
    ["PRÓXIMOS", model.upcoming, false],
    ["COMPLETADOS", model.completed, true],
  ]) {
    if (!items.length) continue;
    fragment.append(
      el(
        "div",
        {
          class:
            "gp-milestone-heading" +
            (completed ? " gp-completed-heading" : "") +
            (completed && model.upcoming.length ? " gp-after-upcoming" : ""),
        },
        title,
      ),
    );
    for (const item of items)
      fragment.append(
        el(
          "div",
          { class: "gp-milestone-row gp-status-" + item.status },
          el("span", { class: "gp-milestone-icon" }, icons[item.status]),
          el(
            "div",
            { class: "gp-milestone-info" },
            el("div", { class: "gp-milestone-name" }, item.name),
            el("div", { class: "gp-milestone-subtitle" }, item.subtitle),
            ...(item.note
              ? [el("div", { class: "gp-milestone-note" }, item.note)]
              : []),
          ),
          el("div", { class: "gp-milestone-date" }, item.date),
        ),
      );
  }
  return fragment;
}
