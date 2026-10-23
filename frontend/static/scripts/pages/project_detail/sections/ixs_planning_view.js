import { el } from "#app/lib/dom.js";
import { h, div, empty, timeline } from "./ixs_executive_view.js";
import { dateText, dateMs, limit, pct } from "./ixs_executive_model.js";
import { icon } from "./ixs_icons.js";
import { planningModel } from "./ixs_planning_model.js";

const button = (text, click, cls = "ixs-btn") =>
  el("button", { class: cls, onclick: click }, ...[text].flat());
const b = (value) => h("b", "", value),
  small = (text) => h("small", "", text);
const head = (title, description, action) =>
  div(
    "ixs-section-head",
    div("", h("h3", "", title), small(description)),
    action,
  );
const card = (...content) => h("section", "ixs-card", content);

function planKpi(
  symbol,
  count,
  title,
  detail,
  accent = "",
  total = 0,
  tag = "",
  progress = count,
) {
  const bar = h("i", "");
  bar.style.width =
    (total ? limit((100 * Number(progress || 0)) / total) : 0) + "%";
  return div(
    `ixs-card ixs-plan-kpi ${accent}`,
    div("top", h("span", "icon", symbol), h("span", "tag", tag || "—")),
    b(count),
    h("strong", "", title),
    small(detail),
    div("meter", bar),
    h("span", "fraction", total ? progress + "/" + total : "—"),
  );
}

function attention(summary, plan, azure) {
  const section = (title, rows, cls) =>
    div(
      `ixs-plan-alert ${cls}`,
      b(rows.length + " " + title),
      rows.length
        ? rows.slice(0, 5).map((x) =>
            el(
              "a",
              {
                class: "ixs-plan-wi",
                href: x.url || "#",
                target: "_blank",
                rel: "noopener noreferrer",
              },
              h("strong", "", `#${x.id ?? ""} · ${x.titulo ?? ""}`),
              small(
                `♙ ${x.asignadoA || "Sin asignar"} · ▣ ${dateText(x.fechaLimiteDev)}`,
              ),
            ),
          )
        : small("Sin Work Items en este grupo."),
    );
  const vacation = div(
    "ixs-plan-alert purple",
    b(`☂ ${summary.vacaciones.length} vacaciones próximas (30 días)`),
    summary.vacaciones.length
      ? summary.vacaciones
          .slice(0, 5)
          .map((x) =>
            div(
              "",
              h("strong", "", x.recurso),
              small(
                `▣ ${dateText(x.inicio)} → ${dateText(x.fin)} · ${x.estado || "Pendiente"}`,
              ),
            ),
          )
      : small("Sin vacaciones próximas."),
  );
  return el(
    "aside",
    { class: "ixs-card ixs-plan-attention", id: "ixs-plan-attention" },
    div(
      "ixs-section-head",
      div(
        "",
        h("h3", "", "♧ Atención requerida"),
        small("Fechas límite Dev y ausencias del proyecto"),
      ),
      h(
        "span",
        "ixs-badge orange",
        summary.late.length + summary.soon.length + summary.vacaciones.length,
      ),
    ),
    ...(azure.cargando
      ? [small("Consultando fechas límite Dev…")]
      : azure.error
        ? [small(azure.error)]
        : [
            section("trabajos vencidos", summary.late, "red"),
            section("próximos a vencer (7 días)", summary.soon, "orange"),
          ]),
    plan.cargando
      ? small("Cargando vacaciones…")
      : plan.error
        ? small(plan.error)
        : vacation,
  );
}

export function renderPlanning(target, data, plan, azure, actions) {
  const m = planningModel(data, plan, azure),
    r = m.summary;
  const loading = azure.cargando,
    vacationLoading = plan.cargando;
  const gantt = el(
    "div",
    { id: "ixs-gantt-historico" },
    timeline(m.timeline, actions.editMarker),
  );
  const timelineCard = h(
    "section",
    "ixs-card ixs-plan-padded",
    head(
      [icon("calendar"), " Línea de tiempo — Hitos principales"],
      "Plan estimado, ejecución real, suspensiones e hitos del proyecto",
      div(
        "ixs-plan-main-actions",
        button([icon("clock"), " Comunicados"], actions.extension),
        button(
          "+ Agregar hito",
          () => actions.edit("compromiso", "", "Hito"),
          "ixs-btn primary",
        ),
      ),
    ),
    gantt,
  );
  const donut = div(
    "ixs-plan-donut",
    div("", b(loading ? "…" : m.items.length), small("To Be / CR")),
  );
  donut.style.background = m.items.length
    ? `conic-gradient(#53b994 0 ${(100 * m.closed) / m.items.length}%,#6334d6 ${(100 * m.closed) / m.items.length}% 100%)`
    : "#eeeaf7";
  const summaryRow = (name, count) =>
    div("ixs-plan-summary-row", h("span", "", name), b(count));
  const vacationRows = plan.vacaciones.map((x) =>
    h(
      "tr",
      "",
      h("td", "", b(x.recurso)),
      h("td", "", dateText(x.inicio)),
      h("td", "", dateText(x.fin)),
      h(
        "td",
        "",
        Math.max(
          1,
          Math.round((dateMs(x.fin) - dateMs(x.inicio)) / 86400000) + 1,
        ),
      ),
      h(
        "td",
        "",
        h(
          "span",
          `ixs-badge ${/aprob/i.test(x.estado) ? "green" : "orange"}`,
          x.estado,
        ),
      ),
      h("td", "", x.comentarios || "—"),
      h("td", "", x.registradoPor || "—"),
      h(
        "td",
        "",
        button("✎", () => actions.edit("vacacion", x.uid)),
      ),
    ),
  );
  const vacations = el(
    "section",
    { id: "ixs-plan-vacaciones", class: "ixs-card ixs-plan-padded" },
    head(
      "Registros de vacaciones",
      "Vacaciones registradas para este proyecto",
      button(
        "+ Registrar vacaciones",
        () => actions.edit("vacacion"),
        "ixs-btn primary",
      ),
    ),
    div(
      "ixs-table-scroll",
      h(
        "table",
        "ixs-table",
        h(
          "thead",
          "",
          h(
            "tr",
            "",
            [
              "Recurso",
              "Inicio",
              "Fin",
              "Días",
              "Estado",
              "Comentarios",
              "Registrado por",
              "Editar",
            ].map((x) => h("th", "", x)),
          ),
        ),
        h(
          "tbody",
          "",
          vacationRows.length
            ? vacationRows
            : h(
                "tr",
                "",
                el("td", { colspan: 8 }, "Sin vacaciones registradas."),
              ),
        ),
      ),
    ),
  );
  target.replaceChildren(
    div(
      "ixs-plan-kpis",
      planKpi(
        "▣",
        m.hitos.length,
        "Hitos totales",
        `${m.completed} completados · ${m.hitos.length - m.completed} pendientes`,
        "green",
        m.hitos.length,
        pct(m.hitos.length ? (100 * m.completed) / m.hitos.length : 0),
        m.completed,
      ),
      planKpi(
        "▷",
        m.underway,
        "En progreso",
        "Fases en ejecución",
        "blue",
        m.hitos.length,
        pct(m.hitos.length ? (100 * m.underway) / m.hitos.length : 0),
      ),
      planKpi(
        "⚠",
        loading ? "…" : r.late.length,
        "Vencidos",
        "Fecha límite Dev",
        "red",
        loading ? 0 : m.dated,
        loading ? "…" : r.late.length ? "Revisar" : "Sin alertas",
      ),
      planKpi(
        "◷",
        loading ? "…" : r.soon.length,
        "Próximos 7 días",
        "Fecha límite Dev",
        "orange",
        loading ? 0 : m.dated,
        "7 días",
      ),
      planKpi(
        "☷",
        loading ? "…" : r.abiertas.length,
        "Work Items abiertos",
        m.items.length + " To Be / CR en total",
        "",
        loading ? 0 : m.items.length,
        "To Be / CR",
      ),
      planKpi(
        "♙",
        vacationLoading ? "…" : r.vacaciones.length,
        "Vacaciones próximas",
        "Próximos 30 días",
        "blue",
        vacationLoading ? 0 : m.resources,
        "30 días",
      ),
    ),
    div(
      "ixs-plan-layout",
      div("ixs-plan-main", timelineCard),
      attention(r, plan, azure),
    ),
    div(
      "ixs-plan-summary",
      card(
        head(
          "▥ Work Items — resumen",
          "Solo To Be y Change Request de este proyecto",
          button("Ver en Azure DevOps ↗", actions.azure),
        ),
        div(
          "ixs-plan-wi-overview",
          donut,
          div(
            "",
            summaryRow("Cerrados", loading ? "…" : m.closed),
            summaryRow("Abiertos", loading ? "…" : r.abiertas.length),
            m.byStage.map(([name, n]) => summaryRow(name, n)),
          ),
        ),
      ),
      card(
        head(
          "♙ Calendario de vacaciones",
          "Recursos ausentes por semana · próximas seis semanas",
          button("Ver todas", () =>
            vacations.scrollIntoView({ behavior: "smooth" }),
          ),
        ),
        div(
          "ixs-plan-vac-weeks",
          m.weeks.map((w) =>
            div(
              `ixs-plan-vac-week ${w.count ? "" : "empty"}`,
              b(w.fecha),
              h("span", "", w.count),
            ),
          ),
        ),
        r.vacaciones.length
          ? r.vacaciones
              .slice(0, 3)
              .map((v) =>
                div(
                  "ixs-plan-vac-entry",
                  div("", b(v.recurso), small(v.estado || "Pendiente")),
                  small(`${dateText(v.inicio)} → ${dateText(v.fin)}`),
                ),
              )
          : empty("Sin vacaciones próximas."),
      ),
    ),
    actions.azureSection(azure),
    vacations,
    ...(plan.cargando ? [empty("Cargando planeación…")] : []),
    ...(plan.error ? [empty(plan.error)] : []),
  );
  target.dataset.renderer = "modular-planning";
}
