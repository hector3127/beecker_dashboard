import { months, num, norm } from "./model.js";
import {
  el,
  node,
  text,
  button,
  heading,
  input,
  select,
  cell,
  download,
} from "./ui.js";

export function percentResources(state, selection, model, actions) {
  const { byPerson, valid } = model.percentResources(),
    bajas = model.bajas();
  const pct = (p, i) =>
    p
      ? (100 * p.fact) / (state.day * model.workdays(i) || 1)
      : valid[i]
        ? 0
        : null;
  const heat = (v) =>
    v == null
      ? "gpr-na"
      : v >= 100
        ? "gpr-green"
        : v >= 80
          ? "gpr-yellow"
          : "gpr-red";
  const rows = Array.from(byPerson.values())
    .filter((r) =>
      norm(r.name + " " + r.area).includes(norm(selection.percentSearch)),
    )
    .sort((a, b) => a.name.localeCompare(b.name, "es"))
    .map((r) => {
      const values = r.months.map(pct),
        used = values.filter((v, i) => r.months[i] && v != null),
        avg = used.length
          ? used.reduce((n, v) => n + v, 0) / used.length
          : null;
      const mark = bajas.has(norm(r.name).replace(/\s+/g, " "))
        ? "gse-baja"
        : "";
      return node(
        "tr",
        null,
        text("th", r.name, mark),
        text("td", r.area, mark),
        values.concat(avg).map((v) => cell(v, heat(v), true)),
      );
    });
  return node(
    "section",
    "gm-card",
    node(
      "header",
      "ga-chart-header",
      heading("Facturabilidad mensual por recurso", "calendar"),
      input(
        {
          id: "gse-percent-search",
          value: selection.percentSearch,
          placeholder: "Buscar recurso o área",
        },
        (v) => actions.set("percentSearch", v, "gse-percent-search"),
        "input",
      ),
    ),
    text(
      "p",
      "Horas facturables / capacidad laboral mensual × 100. Promedio de meses cargados con horas; 0 en meses consultados sin registros y NA si no se consultó.",
      "ga-sub",
    ),
    node(
      "div",
      "gm-table-scroll",
      node(
        "table",
        "gm-table gpr-table",
        node(
          "thead",
          null,
          node(
            "tr",
            null,
            ["Recurso", "Área", ...months, "Promedio"].map((h) =>
              text("th", h),
            ),
          ),
        ),
        node("tbody", null, rows),
      ),
    ),
  );
}

export function detailValues(state, model, row) {
  return row.values.map((h, i) => {
    const r = state.data[model.key(i)];
    return r && r.ok && Array.isArray(r.detalle) ? h : null;
  });
}
function filteredRows(selection, model) {
  const q = norm(selection.detailSearch);
  return model
    .resourceRows()
    .filter((r) => norm(r.recurso + " " + r.proyecto).includes(q));
}
export function detailExport(state, selection, model) {
  const band = selection.detailBand;
  download(
    [
      [
        "Recurso",
        "Banda (" + months[band] + ")",
        "Categoría",
        "Tipo de proyecto",
        "Proyecto",
        ...months,
        "Total horas",
        "Servicio",
      ],
      ...filteredRows(selection, model).map((r) => {
        const v = detailValues(state, model, r);
        return [
          r.recurso,
          r.bands[band] || "NA",
          r.categoria,
          r.tipo,
          r.proyecto,
          ...v.map((h) => (h == null ? "NA" : h)),
          v.reduce((a, h) => a + (h || 0), 0),
          r.servicio || "NA",
        ];
      }),
    ],
    "GSE-Detalle-recursos-" + state.year + ".csv",
  );
}
export function resourceDetail(state, selection, model, actions) {
  const rows = filteredRows(selection, model),
    size = 30,
    pages = Math.max(1, Math.ceil(rows.length / size));
  selection.detailPage = Math.max(0, Math.min(selection.detailPage, pages - 1));
  const band = selection.detailBand,
    totals = Array(12).fill(0);
  rows.forEach((r) =>
    detailValues(state, model, r).forEach((h, i) => {
      if (h != null) totals[i] += h;
    }),
  );
  const total = (r) =>
      detailValues(state, model, r).reduce((a, h) => a + (h || 0), 0),
    cells = (values) =>
      values.map((h) =>
        cell(h, h > 0 ? "gse-hour-positive" : "gse-hour-muted"),
      );
  const table = node(
    "table",
    "gse-resource-table",
    node(
      "thead",
      null,
      node(
        "tr",
        null,
        [
          "Recurso",
          "Banda",
          "Categoría",
          "Tipo de proyecto",
          "Proyecto",
          ...months,
          "Total horas",
          "Servicio",
        ].map((h) => text("th", h)),
      ),
    ),
    node(
      "tbody",
      null,
      rows
        .slice(selection.detailPage * size, (selection.detailPage + 1) * size)
        .map((r) => {
          const low =
            String(r.bands[band] || "")
              .trim()
              .toLowerCase() === "baja";
          return node(
            "tr",
            null,
            text("th", r.recurso, low ? "gse-baja" : ""),
            text("td", r.bands[band] || "NA", low ? "gse-baja-band" : ""),
            text("td", r.categoria),
            node(
              "td",
              null,
              text(
                "span",
                r.tipo,
                "gse-type " +
                  (r.tipo.toLowerCase() === "facturable"
                    ? "gse-type-billable"
                    : "gse-type-other"),
              ),
            ),
            text("td", r.proyecto, "gse-project-id"),
            cells(detailValues(state, model, r)),
            cell(total(r), "gse-hour-total"),
            text("td", r.servicio || "NA"),
          );
        }),
      !rows.length
        ? node(
            "tr",
            null,
            el("td", {
              colspan: 19,
              text: "No hay detalle disponible. Consulta el año para recuperar las horas por proyecto.",
            }),
          )
        : null,
    ),
    node(
      "tfoot",
      null,
      node(
        "tr",
        null,
        text("th", "Total de filas filtradas", "gse-foot-a"),
        text("th", "", "gse-foot-b"),
        el("td", { colspan: 3 }),
        cells(
          totals.map((h, i) =>
            state.data[model.key(i)]?.ok &&
            Array.isArray(state.data[model.key(i)].detalle)
              ? h
              : null,
          ),
        ),
        cell(totals.reduce((a, h) => a + h, 0)),
        text("td", ""),
      ),
    ),
  );
  const body = node(
    "section",
    "gse-resource-dialog",
    node(
      "div",
      "gse-resource-heading",
      node(
        "div",
        null,
        el("h2", {
          id: "gse-resource-title",
          text: "Detalle recursos · " + state.year,
        }),
        text(
          "p",
          (state.area || "Todas las áreas") +
            " · Horas por persona y proyecto de los meses consultados.",
          "gse-note",
        ),
      ),
      el("button", {
        class: "ci-btn",
        id: "gse-resource-close",
        "aria-label": "Cerrar detalle",
        hidden: true,
        text: "Cerrar ×",
      }),
    ),
    node(
      "div",
      "gse-tools",
      node(
        "label",
        null,
        "Buscar persona o proyecto",
        input(
          {
            id: "gse-resource-search",
            placeholder: "Nombre o ID completo",
            value: selection.detailSearch,
          },
          (v) => {
            selection.detailPage = 0;
            actions.set("detailSearch", v, "gse-resource-search");
          },
          "input",
        ),
      ),
      node(
        "label",
        null,
        "Banda del mes",
        select(
          months.map((m, i) => [i, m]),
          band,
          (v) => actions.set("detailBand", Number(v), "gse-resource-band"),
          { id: "gse-resource-band" },
        ),
      ),
      button(
        "Exportar detalle CSV",
        () => detailExport(state, selection, model),
        "ci-btn",
        { id: "gse-resource-export" },
      ),
    ),
    el(
      "div",
      { id: "gse-resource-table", class: "gse-resource-scroll" },
      table,
    ),
    node(
      "div",
      "gse-resource-footer",
      el("span", {
        id: "gse-resource-count",
        text:
          rows.length +
          " filas · Página " +
          (selection.detailPage + 1) +
          " de " +
          pages,
      }),
      node(
        "div",
        null,
        button(
          "← Anterior",
          () => actions.set("detailPage", selection.detailPage - 1),
          "ci-btn",
          { id: "gse-resource-prev", disabled: selection.detailPage === 0 },
        ),
        " ",
        button(
          "Siguiente →",
          () => actions.set("detailPage", selection.detailPage + 1),
          "ci-btn",
          {
            id: "gse-resource-next",
            disabled: selection.detailPage === pages - 1,
          },
        ),
      ),
    ),
    text(
      "p",
      "0: mes consultado sin horas para esta fila. NA: mes sin consultar, fallido o sin detalle. La banda se obtiene por persona y mes de Bandas/rol y se aplica a todos sus proyectos. Las horas se cuentan una sola vez por proyecto; el total suma los meses disponibles.",
      "gse-note",
    ),
  );
  body.setAttribute("role", "dialog");
  body.setAttribute("aria-modal", "true");
  body.setAttribute("aria-labelledby", "gse-resource-title");
  return el(
    "div",
    { id: "gse-resource-modal", class: "gse-inline-view" },
    body,
  );
}
