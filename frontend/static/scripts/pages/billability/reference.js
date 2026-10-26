// @ts-check
import { renderReference } from "./reference_render_view.js";
// controller: billability/reference. Original data, ordering and interactions are preserved.
import { el, svg } from "#app/lib/dom.js";
import { number, fmt } from "./reference_model.js";
import { icon, sparkline } from "./reference_view.js";
export function mountReference() {
  const old = document.querySelector(".bars");
  if (!old) return;
  const months = [...old.children].map((node) => ({
    month: node.dataset.month,
    label: node.dataset.label,
    short: node.lastChild.textContent.trim(),
    percent: number(node.dataset.percent),
    fixed: number(node.dataset.fixed),
    variable: number(node.dataset.variable),
    fixedPercent: number(node.dataset.fixedPercent),
    variablePercent: number(node.dataset.variablePercent),
    selected: node.classList.contains("cu"),
  }));
  const cards = [...document.querySelectorAll(".hero>.kc,.hero>.tot")];
  cards.forEach((card, index) => {
    const copy = el("div", { class: "bill-kpi-copy" }, ...card.childNodes);
    card.append(icon(["bars", "file", "globe"][index]), copy);
    if (index < 2) {
      const plot = sparkline(
        months.map((month) =>
          index ? month.variablePercent : month.fixedPercent,
        ),
        index,
      );
      if (plot) card.append(plot);
    } else
      card.append(
        el(
          "span",
          { class: "bill-total-decoration", "aria-hidden": "true" },
          el("i"),
          el("i"),
          el("i"),
        ),
      );
  });
  const table = document.querySelector(".sc table");
  table.id = "bill-summary";
  [...table.tBodies[0].rows].forEach((row) => {
    const cell = row.cells[row.cells.length - 1],
      raw = number(cell.textContent.trim().replace("%", ""));
    if (raw === null) return;
    cell.replaceChildren(
      el("span", {
        class: `bill-global-pill ${raw >= 70 ? "good" : "warning"}`,
        text: cell.textContent.trim(),
      }),
    );
  });
  const section = old.closest("section");
  section.id = "bill-chart-card";
  section.classList.add("bill-chart-card");
  const title = section.querySelector("h2"),
    description = section.querySelector(".hs");
  const percent = el("button", {
      id: "bill-mode-percent",
      type: "button",
      text: "% Facturabilidad",
      "aria-pressed": "true",
    }),
    hours = el("button", {
      id: "bill-mode-hours",
      type: "button",
      text: "Horas facturadas",
      "aria-pressed": "false",
    });
  const expand = el("button", {
    id: "bill-chart-expand",
    class: "bill-chart-expand",
    type: "button",
    "aria-label": "Ampliar gráfica",
    "aria-expanded": "false",
    text: "⤢",
  });
  const header = el(
    "div",
    { class: "bill-chart-heading" },
    icon("globe"),
    el("div", { class: "bill-chart-heading-copy" }, title, description),
    el(
      "div",
      { class: "bill-chart-controls" },
      el("div", { class: "bill-chart-mode" }, percent, hours),
      expand,
    ),
  );
  const plot = el("div", { class: "bill-chart-plot" }),
    aside = el("aside", { class: "bill-chart-aside", "aria-live": "polite" }),
    legend = el("div", { class: "bill-chart-legend" });
  section.replaceChildren(
    header,
    el("div", { class: "bill-chart-body" }, plot, aside),
    legend,
  );
  let mode = "percent",
    selected = months.findLastIndex((month) => month.selected);
  if (selected < 0) selected = months.length - 1;
  const amount = (month) =>
    mode === "percent"
      ? month.percent
      : month.fixed === null || month.variable === null
        ? null
        : month.fixed + month.variable;
  function render() {
    return renderReference({
      get percent() {
        return percent;
      },
      get mode() {
        return mode;
      },
      set mode(value) {
        mode = value;
      },
      get hours() {
        return hours;
      },
      get months() {
        return months;
      },
      get amount() {
        return amount;
      },
      get plot() {
        return plot;
      },
      get section() {
        return section;
      },
      get selected() {
        return selected;
      },
      set selected(value) {
        selected = value;
      },
      get render() {
        return render;
      },
      get aside() {
        return aside;
      },
      get legend() {
        return legend;
      },
    });
  }
  percent.addEventListener("click", () => {
    mode = "percent";
    render();
  });
  hours.addEventListener("click", () => {
    mode = "hours";
    render();
  });
  expand.addEventListener("click", () => {
    const expanded = section.classList.toggle("bill-chart-expanded");
    expand.setAttribute("aria-expanded", String(expanded));
    expand.setAttribute(
      "aria-label",
      expanded ? "Reducir gráfica" : "Ampliar gráfica",
    );
    render();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      section.classList.remove("bill-chart-expanded");
      expand.setAttribute("aria-expanded", "false");
      expand.setAttribute("aria-label", "Ampliar gráfica");
      render();
    }
  });
  render();
  let plotWidth = plot.clientWidth;
  new ResizeObserver(() => {
    const width = plot.clientWidth;
    if (width !== plotWidth) {
      plotWidth = width;
      render();
    }
  }).observe(plot);
}
