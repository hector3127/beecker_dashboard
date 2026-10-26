import { el } from "#app/lib/dom.js";
import { tasksModel, raidModel } from "./generic_sources_model.js";

export const sourceError = (text) => el("div", { class: "gs-error" }, text);

export function taskNodes(result) {
  const model = tasksModel(result);
  const investment = (label, value, commercial = false) =>
    el(
      "div",
      {
        class: "gs-investment" + (commercial ? " gs-commercial" : ""),
      },
      el("div", { class: "gs-investment-label" }, label),
      el("div", { class: "gs-investment-value" }, value),
    );
  const nodes = [
    el(
      "div",
      { class: "gs-investments" },
      investment("INV_OPERATIVA", model.operational),
      investment("INV_COMERCIAL", model.commercial, true),
    ),
    el(
      "div",
      { class: "gs-task-head" },
      el("span", { class: "gs-task-title" }, model.heading),
      el(
        "span",
        { class: "gs-task-total" },
        "Total: ",
        el("b", {}, model.total),
      ),
    ),
  ];
  if (model.range)
    nodes.push(el("div", { class: "gs-task-range" }, model.range));
  nodes.push(
    el(
      "div",
      { class: "gs-task-scroll" },
      ...(model.withHours.length
        ? model.withHours.map((row) =>
            el(
              "div",
              {
                class: "gs-task-row",
              },
              el("span", { class: "gs-task-name" }, row.name),
              el("b", { class: "gs-task-hours" }, row.hours),
            ),
          )
        : [
            el(
              "div",
              { class: "gs-task-empty" },
              "Sin horas asociadas a Tasks.",
            ),
          ]),
    ),
  );
  if (model.withoutHours.length)
    nodes.push(
      el(
        "details",
        { class: "gs-task-details" },
        el("summary", {}, `Ver tasks sin horas (${model.withoutHours.length})`),
        el(
          "div",
          { class: "gs-zero-list" },
          ...model.withoutHours.map((name) =>
            el(
              "div",
              {
                class: "gs-zero-row",
              },
              el("span", {}, name),
              el("span", {}, "0 h"),
            ),
          ),
        ),
      ),
    );
  return nodes;
}

export function raidNode(result) {
  const model = raidModel(result);
  if (!model.rows.length)
    return el(
      "div",
      { class: "gs-raid-empty" },
      "Sin riesgos Active / Proposed en Azure.",
    );
  return el(
    "table",
    { class: "data-table" },
    el(
      "thead",
      {},
      el(
        "tr",
        {},
        ...["Riesgo", "Impacto", "Probabilidad"].map((heading) =>
          el("th", {}, heading),
        ),
      ),
    ),
    el(
      "tbody",
      {},
      ...model.rows.map((row) =>
        el(
          "tr",
          {},
          el(
            "td",
            {},
            row.description,
            el("div", { class: "gs-risk-detail" }, row.detail),
          ),
          el("td", {}, el("span", { class: "badge " + row.badge }, row.impact)),
          el("td", {}, row.probability),
        ),
      ),
    ),
  );
}
