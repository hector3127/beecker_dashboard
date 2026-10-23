import { el } from "#app/lib/dom.js";
import { h, div, kpi } from "./ixs_executive_view.js";
import { pct, dateText } from "./ixs_executive_model.js";
import { statusClass } from "./ixs_planning_azure.js";
import { statusColors } from "./ixs_azure_summary_model.js";

const empty = (text) => div("ixs-azure-empty", text);
const track = (width) => {
  const fill = h("i", "");
  fill.style.width = width + "%";
  return div("track", fill);
};
const swatch = (name, cls = "sw") => {
  const node = h("span", cls);
  node.style.background = statusColors[name];
  return node;
};

// Match the original collapse limits and labels. Hidden content remains in DOM.
function expandable(box, rows, visible, content) {
  const more = Math.max(0, rows.length - visible);
  box.dataset.expanded = "0";
  box.dataset.moreCount = String(more);
  rows.slice(visible).forEach((row) => {
    row.dataset.ixsMore = "1";
    row.style.display = "none";
  });
  box.replaceChildren(...content);
  if (more) {
    const button = el(
      "button",
      {
        type: "button",
        class: "ixs-btn",
        onclick: () => {
          const expanded = box.dataset.expanded === "1";
          box.dataset.expanded = expanded ? "0" : "1";
          rows.slice(visible).forEach((row) => {
            row.style.display = expanded ? "none" : "";
          });
          button.textContent = expanded ? `Ver más (${more})` : "Ver menos";
        },
      },
      `Ver más (${more})`,
    );
    const footer = div("ixs-azure-more-footer", button);
    // In the stale panel the footer belongs inside its scroll wrapper.
    if (box.id === "ixs-azure-stale") content[0].append(footer);
    else box.append(footer);
  }
}

export function renderAzureSummary(root, m) {
  const get = (id) => root.querySelector("#" + id);
  get("ixs-azure-kpis")?.replaceChildren(
    kpi(
      "layers",
      "Work items del proyecto",
      m.total,
      "Total consultado en Azure",
      null,
    ),
    kpi(
      "clock",
      "Sin seguimiento +7 días",
      m.staleCount,
      m.staleCount ? "Requieren seguimiento" : "Todo al día",
      null,
      m.staleCount ? "red" : "green",
    ),
    kpi(
      "warning",
      "En riesgo",
      m.riskCount,
      m.riskCount ? "Con alerta o bloqueo" : "Sin alertas críticas",
      null,
      m.riskCount ? "red" : "green",
    ),
    kpi(
      "check",
      "Cerrados",
      m.closed,
      m.total ? `${pct((m.closed * 100) / m.total)} del total` : "Sin datos",
      null,
      "green",
    ),
    kpi(
      "target",
      "QA listos",
      m.qa,
      m.total ? `${pct((m.qa * 100) / m.total)} del total` : "Sin datos",
      null,
    ),
    kpi(
      "chart",
      "Avance promedio",
      m.avg + "%",
      "To Be / Change Request",
      m.avg,
      m.avg >= 80 ? "green" : m.avg >= 50 ? "" : "red",
    ),
  );
  const donut = div(
    "ixs-donut",
    div("ixs-donut-center", h("b", "", m.total), h("small", "", "Work Items")),
  );
  donut.style.background = m.donut;
  const notes = m.notes.map((n) =>
    h(
      "p",
      "ixs-azure-health-note",
      h(
        "span",
        `dot ${n.cls}`,
        n.cls === "bad" || n.cls === "warn" ? "!" : "✓",
      ),
      h("span", "", n.text),
    ),
  );
  const legend = m.entries.map(([name, value]) =>
    div(
      "ixs-az85-legend-item",
      swatch(name),
      h("span", "name", name),
      h("b", "", value),
      h("small", "", Math.round((value * 100) / m.totalDist) + "%"),
    ),
  );
  get("ixs-azure-health")?.replaceChildren(
    div(
      "ixs-azure-health-v85",
      donut,
      div("ixs-az85-quick", notes),
      div("ixs-az85-legend", legend),
    ),
  );
  const stale = get("ixs-azure-stale");
  if (stale) {
    if (!m.staleCount)
      stale.replaceChildren(
        empty(
          "Todo al día: no hay work items sin seguimiento por más de 7 días.",
        ),
      );
    else {
      const rows = m.staleSorted.map((item) =>
        h(
          "tr",
          "",
          h(
            "td",
            "",
            item.url
              ? el(
                  "a",
                  {
                    class: "ixs-azure-idlink",
                    href: item.url,
                    target: "_blank",
                    rel: "noopener noreferrer",
                    title: `Abrir Work Item #${item.id ?? ""} en Azure DevOps`,
                  },
                  "#" + (item.id ?? ""),
                )
              : h("b", "", "#" + (item.id ?? "")),
          ),
          h("td", "", item.titulo ?? ""),
          h("td", "", item.tipo || "—"),
          h(
            "td",
            "",
            h(
              "span",
              `ixs-azure-badge ${statusClass(item.estado)}`,
              item.estado || "—",
            ),
          ),
          h("td", "", item.asignadoA || "—"),
          h("td", "", dateText(item.ultimoSeguimiento)),
          h(
            "td",
            "",
            h(
              "span",
              `days ${(Number(item.diasSinActualizar) || 0) < 14 ? "warn" : ""}`,
              `${Number(item.diasSinActualizar) || 0} días`,
            ),
          ),
        ),
      );
      const table = h(
        "table",
        "",
        h(
          "thead",
          "",
          h(
            "tr",
            "",
            [
              "#",
              "Título",
              "Tipo",
              "Estado",
              "Asignado",
              "Último seguimiento",
              "Días sin actualizar",
            ].map((x) => h("th", "", x)),
          ),
        ),
        h("tbody", "", rows),
      );
      expandable(stale, rows, 3, [div("ixs-azure-stale", table)]);
    }
  }
  const assigned = get("ixs-azure-by-assignee");
  if (assigned) {
    if (!m.byAssigned.length)
      assigned.replaceChildren(empty("Sin responsables registrados."));
    else {
      const rows = m.byAssigned.map((x) =>
        div(
          "ixs-az85-load-row",
          div(
            "ixs-az85-load-meta",
            h("b", "", x.nombre),
            h(
              "small",
              "",
              `${x.abiertos} abiertos · ${x.cerrados} cerrados · ${x.total} en total`,
            ),
          ),
          track((x.abiertos * 100) / m.maxOpen),
          h("span", "ixs-az85-load-count", `${x.abiertos}/${x.total}`),
        ),
      );
      expandable(assigned, rows, 5, [
        div("ixs-az85-load", rows),
        div(
          "ixs-az85-load-note",
          "Carga = número de Work Items abiertos de cada persona. No representa horas disponibles ni porcentaje de capacidad laboral.",
        ),
      ]);
    }
  }
  const dates = get("ixs-azure-dates");
  if (dates) {
    if (!m.byDate.length)
      dates.replaceChildren(empty("Sin fechas límite registradas."));
    else {
      const rows = m.byDate.map((x) =>
        el(
          "a",
          {
            class: "ixs-az85-date-item",
            href: x.url,
            target: "_blank",
            rel: "noopener noreferrer",
          },
          h("time", "", dateText(x.fecha)),
          h(
            "span",
            "ixs-az85-date-detail",
            h("b", "", x.req || "Sin requisito"),
            h("small", "", x.titulo || "Sin título"),
          ),
        ),
      );
      expandable(dates, rows, 5, [div("ixs-az85-date-list", rows)]);
    }
  }
  get("ixs-azure-status-summary")?.replaceChildren(
    ...(m.entries.length
      ? m.entries.map(([name, value]) =>
          div(
            "row",
            h(
              "span",
              "ixs-azure-status-label",
              swatch(name, "sw ixs-azure-status-swatch"),
              name,
            ),
            track((100 * value) / m.totalDist),
            h("small", "", value),
          ),
        )
      : [empty("Sin distribución disponible.")]),
  );
}
