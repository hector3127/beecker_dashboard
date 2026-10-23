import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";
import { num, pct, limit } from "./ixs_executive_model.js";
import {
  h,
  div,
  empty,
  kpi,
  heading,
  metric,
  balanceBadge,
  miniHours,
} from "./ixs_executive_view.js";
import { effortModel } from "./ixs_effort_model.js";

const small = (text) => h("small", "", text);
const b = (text) => h("b", "", text);

export function effortResources(rows = []) {
  const td = (value) => h("td", "", value);
  return div(
    "ixs-table-scroll",
    h(
      "table",
      "ixs-table ixs-effort-resource-table",
      h(
        "thead",
        "",
        h(
          "tr",
          "",
          [
            "Recurso",
            "Rol",
            "Reales",
            "Fact.",
            "No fact.",
            "Balance",
            "% cumpl.",
            "Estado",
          ].map((x) => h("th", "", x)),
        ),
      ),
      h(
        "tbody",
        "",
        rows.length
          ? rows.map((x) =>
              h(
                "tr",
                "",
                el(
                  "td",
                  x.activo === false
                    ? {
                        class: "ixs-exec-inactive",
                        title: "Recurso inactivo en el proyecto",
                      }
                    : {},
                  x.nombre || "—",
                ),
                td(x.posicion || "—"),
                td(num(x.horasReales, 2)),
                td(
                  num(
                    Math.max(
                      0,
                      Number(x.horasReales || 0) - Number(x.horasNoFact || 0),
                    ),
                    2,
                  ),
                ),
                td(num(x.horasNoFact, 2)),
                td(balanceBadge(x.balance)),
                td(pct(x.pctCumplimiento)),
                td(
                  h(
                    "span",
                    `ixs-badge ${/exced|retras/i.test(String(x.estado || "")) ? "red" : /riesgo/i.test(String(x.estado || "")) ? "orange" : "green"}`,
                    x.estado || "—",
                  ),
                ),
              ),
            )
          : h("tr", "", el("td", { colspan: 8 }, "Sin datos disponibles.")),
      ),
    ),
  );
}

export function renderEffort(target, data) {
  const rows = data.filasRecursosCompleto || [],
    roles = data.porRol || [],
    p = data.proyecto || {},
    eff = effortModel(data);
  const balancePct = eff.estimadas
    ? (Math.max(0, eff.balance) * 100) / eff.estimadas
    : 0;
  const balance = kpi(
    "target",
    "Balance restante",
    num(eff.balance, 2) + " h",
    "Horas por consumir",
    balancePct,
    "purple",
  );
  balance.append(div("ixs-effort-kpi-extra", b(pct(balancePct))));
  const donut = div(
    "ixs-donut",
    div("ixs-donut-center", b(num(eff.real, 2) + " h"), small("Total")),
  );
  donut.style.background = `conic-gradient(#6033d9 0 ${limit(eff.pctFact)}%,#ed2791 ${limit(eff.pctFact)}% 100%)`;
  const areaRow = (label, value, percent, cls) =>
    div(
      "ixs-area-row",
      h("i", `sw ${cls}`),
      h("span", "name", label),
      b(num(value, 2) + " h"),
      small(pct(percent)),
    );
  const checks = [
    [
      eff.pctConsumo <= 100 ? "" : "bad",
      eff.pctConsumo <= 100
        ? "El consumo sigue por debajo del plan total."
        : "El consumo rebasa el plan de horas.",
    ],
    [
      eff.pctFact >= 50 ? "" : "warn",
      eff.pctFact >= 50
        ? "La mayoría de las horas son facturables."
        : "Conviene revisar la proporción no facturable.",
    ],
    [
      eff.fueraHorario ? "warn" : "",
      eff.fueraHorario
        ? "Se registraron " + num(eff.fueraHorario, 2) + " h fuera de horario."
        : "No se registran horas fuera de horario en esta fuente.",
    ],
  ];
  const card = (name, title, content) =>
    h("section", "ixs-card", heading(name, title), content);
  const pending = (id, text) =>
    el("div", { id, class: "ixs-card" }, empty(text));
  target.replaceChildren(
    div(
      "ixs-effort-kpis6",
      kpi(
        "clock",
        "Horas reales",
        num(eff.real, 2) + " h",
        "Planeadas: " + num(eff.estimadas, 2) + " h",
        eff.pctConsumo,
        "purple",
      ),
      kpi(
        "layers",
        "Facturables",
        num(eff.fact, 2) + " h",
        pct(eff.pctFact) + " de las horas reales",
        eff.pctFact,
        "purple",
      ),
      kpi(
        "list",
        "No facturables",
        num(eff.noFact, 2) + " h",
        pct(eff.pctNoFact) + " de las horas reales",
        eff.pctNoFact,
        "red",
      ),
      kpi(
        "clock",
        "Fuera de horario",
        num(eff.fueraHorario, 2) + " h",
        pct(eff.pctFuera) + " de las horas reales",
        eff.pctFuera,
        "purple",
      ),
      balance,
    ),
    div(
      "ixs-grid2 ixs-effort-charts",
      h(
        "section",
        "ixs-card",
        heading("donut", "Mix de horas", small("Horas reales")),
        div(
          "ixs-effort-title-note ixs-effort-mix-note",
          "Distribución de las horas reales del proyecto",
        ),
        div(
          "ixs-effort-mix-content",
          donut,
          div(
            "ixs-effort-mix-legend",
            areaRow("Facturables", eff.fact, eff.pctFact, "ixs-effort-fact"),
            areaRow(
              "No facturables",
              eff.noFact,
              eff.pctNoFact,
              "ixs-effort-nonfact",
            ),
          ),
        ),
      ),
      h(
        "section",
        "ixs-card",
        heading("chart", "Resumen de consumo", small(p.id || "Proyecto")),
        div(
          "ixs-effort-summary",
          div(
            "ixs-effort-metrics",
            metric("Consumo de horas", eff.pctConsumo),
            metric("Facturable", eff.pctFact, pct(eff.pctFact), "#6233dd"),
            metric(
              "No facturable",
              eff.pctNoFact,
              pct(eff.pctNoFact),
              "#ee2794",
            ),
            metric(
              "Fuera de horario",
              eff.pctFuera,
              pct(eff.pctFuera),
              "#8058ed",
            ),
          ),
          h(
            "aside",
            "ixs-effort-quick",
            h("h4", "", icon("warning"), " Lectura rápida"),
            checks.map(([tone, text]) =>
              h(
                "p",
                "",
                h(
                  "span",
                  `dot ${tone}`,
                  tone === "bad" ? "!" : tone === "warn" ? "•" : "✓",
                ),
                h("span", "", text),
              ),
            ),
          ),
        ),
        div(
          "ixs-effort-foot",
          b("Balance:"),
          " " + num(eff.balance, 2) + " h · ",
          b("Costo real:"),
          " $" + num(eff.costoReal, 2) + " · ",
          b("% financiero:"),
          " " + pct(eff.costoPct),
        ),
      ),
    ),
    h(
      "section",
      "ixs-card ixs-exec-workload",
      heading(
        "people",
        "Detalle de consumo por recurso",
        small("Reales, facturables, no facturables y balance"),
      ),
      div("ixs-effort-compact", effortResources(rows)),
    ),
    div(
      "ixs-grid2 ixs-effort-charts",
      pending("ixs-actividad-card", "Consultando distribución por actividad…"),
      pending("ixs-tendencia-card", "Consultando tendencia de horas…"),
    ),
    div(
      "ixs-grid2 ixs-effort-bottom",
      pending("ixs-registros-card", "Consultando registros de Clockify…"),
      card(
        "link",
        "Horas Clockify — Task / inversión",
        el(
          "div",
          { id: "ixs-tasks-effort", class: "ixs-empty" },
          "Consultando horas por task…",
        ),
      ),
    ),
    div(
      "ixs-grid2 ixs-effort-charts",
      card(
        "chart",
        "Horas por recurso",
        miniHours(
          rows.map((x) => ({
            nombre: (x.nombre || "") + (x.posicion ? " — " + x.posicion : ""),
            horasReales: x.horasReales,
            horasEstimadas: x.horasEstimadas,
          })),
        ),
      ),
      card(
        "people",
        "Horas por rol",
        miniHours(
          roles.map((x) => ({
            nombre: x.rol,
            horasReales: x.horasReales,
            horasEstimadas: x.horasEstimadas,
          })),
        ),
      ),
    ),
  );
  target.dataset.renderer = "modular-effort";
}
