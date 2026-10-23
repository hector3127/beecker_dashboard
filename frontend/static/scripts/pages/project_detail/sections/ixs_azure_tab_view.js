import { el } from "#app/lib/dom.js";
import { h, div, heading } from "./ixs_executive_view.js";

const box = (id, text) => el("div", { id, class: "ixs-azure-empty" }, text);
const card = (name, title, description, id, text, cls = "") =>
  h(
    "section",
    `ixs-card ${cls}`,
    heading(name, title, description ? h("small", "", description) : null),
    box(id, text),
  );

export function azureTabView(table, refresh) {
  return [
    el(
      "div",
      { class: "ixs-kpis ixs-azure-kpis", id: "ixs-azure-kpis" },
      div("ixs-card ixs-kpi", div("desc", "Cargando KPIs de Azure DevOps…")),
    ),
    div(
      "ixs-main",
      h(
        "section",
        "ixs-card",
        heading(
          "clock",
          "Atención prioritaria",
          el(
            "a",
            {
              href: "#",
              class: "ixs-btn",
              onclick: (event) => {
                event.preventDefault();
                refresh();
              },
            },
            "↻ Actualizar Azure",
          ),
        ),
        box("ixs-azure-stale", "Consultando work items sin seguimiento…"),
      ),
      card(
        "donut",
        "Distribución y salud",
        "Resumen del proyecto en Azure DevOps",
        "ixs-azure-health",
        "Cargando distribución…",
      ),
    ),
    table,
    div(
      "ixs-az84-groups",
      card(
        "people",
        "Ítems por persona / iteración",
        "Responsables agrupados · despliega para ver iteraciones",
        "ixs-az84-person",
        "Consultando iteraciones y responsables…",
      ),
      card(
        "chart",
        "WIs abiertos por etapa",
        "Estados pendientes según Azure",
        "ixs-az84-stage",
        "Consultando iteraciones y estados…",
      ),
    ),
    div(
      "ixs-azure-bottom",
      card(
        "people",
        "Carga por asignado",
        "",
        "ixs-azure-by-assignee",
        "Cargando…",
        "ixs-azure-mini-card",
      ),
      card(
        "calendar",
        "Próximas fechas",
        "",
        "ixs-azure-dates",
        "Cargando…",
        "ixs-azure-mini-card ixs-az85-dates-card",
      ),
      card(
        "target",
        "Resumen de estatus",
        "",
        "ixs-azure-status-summary",
        "Cargando…",
        "ixs-azure-mini-card",
      ),
    ),
  ];
}
