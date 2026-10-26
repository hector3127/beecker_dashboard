import { el } from "#app/lib/dom.js";
import { genericHeaderModel } from "./generic_header_model.js";
const div = (cls, ...children) => el("div", { class: cls }, ...children);
const svg = (tag, props, ...children) => {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(props))
    node.setAttribute(key, String(value));
  node.append(...children);
  return node;
};
function progressCircle(model) {
  return svg(
    "svg",
    { width: 76, height: 76, viewBox: "0 0 76 76" },
    svg("circle", {
      cx: 38,
      cy: 38,
      r: 33.5,
      fill: "none",
      stroke: "#EDEDEF",
      "stroke-width": 9,
    }),
    svg("circle", {
      cx: 38,
      cy: 38,
      r: 33.5,
      fill: "none",
      stroke: "#4A2A94",
      "stroke-width": 9,
      "stroke-dasharray": model.arc + " " + model.rest,
      "stroke-linecap": "round",
      transform: "rotate(-90 38 38)",
    }),
    svg(
      "text",
      { x: 38, y: 43, "text-anchor": "middle", class: "gh-donut-label" },
      model.label,
    ),
  );
}
export function genericHeader(data, context) {
  const model = genericHeaderModel(data, context);
  const field = (icon, label, ...contents) =>
    div(
      "gh-field",
      el("span", { class: "gh-field-icon" }, icon),
      el("div", {}, div("gh-field-label", label), ...contents),
    );
  const header = div(
    "card gh-header",
    div(
      "gh-fields",
      field(
        "💼",
        "Proyecto",
        div("gh-project", model.project),
        div("gh-client", model.client),
      ),
      field("📅", "Fecha de Corte", div("gh-field-value", model.cut)),
      field("👥", "Sponsor", div("gh-field-value", model.sponsor)),
      field(
        "👤",
        "Project Manager",
        div("gh-field-value", model.manager),
        ...(model.delivery ? [div("gh-delivery", model.delivery)] : []),
      ),
    ),
  );
  const card = (title, ...contents) =>
    div("kpi-card", div("kpi-label", title), ...contents);
  const kpis = div(
    "kpi-grid gh-kpis",
    card(
      "Estado General",
      el(
        "div",
        {
          class: "gh-state-icon",
          style: { background: model.color + "1a", color: model.color },
        },
        "✓",
      ),
      el(
        "div",
        { class: "gh-state", style: { color: model.color } },
        model.state,
      ),
    ),
    card(
      "% Avance",
      div("gh-donut", progressCircle(model.progress)),
      ...(model.planned ? [div("kpi-sub", model.planned)] : []),
    ),
    card(
      "Índice de Ritmo",
      div("kpi-value gh-number", model.pace),
      div("kpi-sub " + (model.paceDown ? "down" : ""), model.paceText),
    ),
    el(
      "div",
      { class: "kpi-card", id: "kpi-cumpl-financiero-card" },
      div("kpi-label", "% Cumpl. Financiero"),
      div("kpi-value gh-number", model.financial),
      div("kpi-sub", "Real vs estimado"),
    ),
    div(
      "kpi-card destacada gh-budget",
      div("kpi-label", "Presupuesto (Hrs)"),
      div("kpi-value", model.budget),
      div(
        "progress-bar-bg gh-budget-bg",
        el("div", {
          class: "progress-bar-fill gh-budget-fill",
          style: { width: model.budgetWidth },
        }),
      ),
      div(
        "kpi-sub gh-budget-sub",
        `Gastado: ${model.burn} · Resta: ${model.remaining}`,
      ),
    ),
    card(
      model.exitTitle,
      div("gh-exit-date", model.exitDate),
      el(
        "div",
        { class: "gh-exit-sub" },
        ...(model.exitClass
          ? [el("span", { class: model.exitClass }, model.exitText)]
          : [model.exitText]),
      ),
    ),
  );
  return { header, kpis };
}
