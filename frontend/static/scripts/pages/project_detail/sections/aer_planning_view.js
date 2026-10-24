import {
  h,
  div,
  styled,
  table,
  cell,
  text,
  dateText,
} from "./aer_planning_dom.js";
import { timeline } from "./aer_planning_timeline.js";
import { activitiesTable, vacationTable } from "./aer_planning_tables.js";

const title = (name, sub, bubble) =>
  div(
    "aer-card-title-row",
    div("", h("h3", "", name), div("aer-sub", sub)),
    ...(bubble != null ? [h("span", "bubble", String(bubble))] : []),
  );
const kpi = (icon, label, value, sub, cls = "") =>
  div(
    `aer-plan-kpi ${cls}`,
    div("top", h("span", "icon", icon), h("span", "", label)),
    div("value", String(value)),
    div("sub", sub),
  );
const pct = (n) => `${Math.round(Number(n || 0) * 10) / 10}%`;
const dateShort = (iso) =>
  new Date(iso + "T12:00:00").toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
  });

function attention(m) {
  const items = (rows, kind, limit) =>
    rows
      .slice(0, limit)
      .map((x) =>
        div(
          `aer-attn-item ${kind}`,
          h("span", "dot"),
          h(
            "span",
            "txt",
            h("b", "", text(x.actividad)),
            h("small", "", text(x.responsable || "Sin responsable")),
          ),
          h("span", "date", dateText(x.finPlan)),
        ),
      );
  const section = (
    cls,
    icon,
    label,
    rows,
    empty,
    mini = "",
    bodyNote = false,
  ) =>
    div(
      `aer-attn-section ${cls}`,
      div(
        "title",
        h(
          "span",
          "left",
          h("span", "iconball", icon),
          h(
            "span",
            "",
            ...(mini
              ? [h("span", "", label), h("span", "mini", mini)]
              : [label]),
          ),
        ),
        h("span", "chev", "›"),
      ),
      ...(rows.length
        ? [div("aer-attn-items", ...rows)]
        : [
            div(
              bodyNote ? "body-note" : "aer-attn-items",
              ...(bodyNote ? [empty] : [div("aer-attn-empty", empty)]),
            ),
          ]),
    );
  // Original markup nests an extra span in the upcoming section even without a date.
  const upcomingLabel = h(
    "span",
    "",
    `${m.proximos7.length} próximo${m.proximos7.length === 1 ? "" : "s"} a vencer`,
  );
  const reference = m.proximos7.length
    ? dateText(
        m.proximos7.reduce((a, b) =>
          new Date(a.finPlan) <= new Date(b.finPlan) ? a : b,
        ).finPlan,
      )
    : "";
  const upcoming = div(
    "aer-attn-section orange",
    div(
      "title",
      h(
        "span",
        "left",
        h("span", "iconball", "!"),
        h(
          "span",
          "",
          upcomingLabel,
          ...(reference ? [h("span", "mini", `Vencen el ${reference}`)] : []),
        ),
      ),
      h("span", "chev", "›"),
    ),
    div(
      "aer-attn-items",
      ...(m.proximos7.length
        ? items(m.proximos7, "orange", 4)
        : [div("aer-attn-empty", "Sin compromisos próximos a vencer.")]),
    ),
  );
  const blocks = m.depUnique
    .filter((x) => x.status === "Detenida")
    .slice(0, 3)
    .map((x) =>
      div(
        "aer-attn-item green",
        h("span", "dot"),
        h(
          "span",
          "txt",
          h("b", "", text(x.label)),
          h("small", "", `${x.rows.length} actividad(es) relacionada(s)`),
        ),
        h("span", "date", "Detenido"),
      ),
    );
  const vacations = m.vacacionesProximas
    .slice(0, 3)
    .map((v) =>
      div(
        "aer-attn-item green",
        h("span", "dot"),
        h(
          "span",
          "txt",
          h("b", "", text(v.recurso)),
          h("small", "", text(v.estado || "Aprobada")),
          h("span", "impact", "Afecta capacidad"),
        ),
        h("span", "date", `${dateText(v.inicio)} → ${dateText(v.fin)}`),
      ),
    );
  return div(
    "aer-card aer-plan-attn",
    div(
      "aer-attn-head",
      div(
        "",
        h("h3", "", "Atención requerida"),
        div("aer-sub", "Elementos que necesitan tu atención"),
      ),
      h("span", "badge-count", String(m.attnCount)),
    ),
    div(
      "aer-attn-list",
      section(
        "red",
        "!",
        `${m.vencidosRows.length} vencido${m.vencidosRows.length === 1 ? "" : "s"}`,
        items(m.vencidosRows, "red", 3),
        "Sin compromisos vencidos.",
      ),
      upcoming,
      section(
        "purple",
        "◇",
        `${m.hitosValidar.length} hito${m.hitosValidar.length === 1 ? "" : "s"} por validar`,
        items(m.hitosValidar, "purple", 4),
        "Sin hitos pendientes por validar.",
      ),
      section(
        "green",
        "✓",
        `${m.bloqueosCriticos} bloqueo${m.bloqueosCriticos === 1 ? "" : "s"} crítico${m.bloqueosCriticos === 1 ? "" : "s"}`,
        blocks,
        "No hay bloqueos críticos en este momento.",
        "",
        true,
      ),
      section(
        "green",
        "☂",
        `${m.vacacionesProximas.length} vacaciones próximas`,
        vacations,
        "No hay vacaciones próximas registradas.",
        "",
        true,
      ),
    ),
  );
}

function secondary(m) {
  const next = div(
    "aer-card",
    title(
      "Próximos compromisos",
      "Actividades e hitos que vencen próximamente.",
      m.proximos.length,
    ),
    ...(m.proximos.length
      ? m.proximos
          .slice(0, 5)
          .map((x) =>
            div(
              "aer-minirow",
              h(
                "span",
                "",
                h("b", "", text(x.actividad)),
                h("br", ""),
                h("small", "", text(x.responsable || "")),
              ),
              styled(h("b", "", dateText(x.finPlan)), { color: "#e22f49" }),
            ),
          )
      : [div("aer-sub", "Sin próximos compromisos.")]),
  );
  const progress = (value, width, color) =>
    styled(
      div(
        "",
        h("b", "", value + "%"),
        div(
          "aer-occ-bar",
          styled(h("i", ""), { width: width + "%", background: color }),
        ),
      ),
      {
        display: "grid",
        gridTemplateColumns: "36px 1fr",
        gap: "6px",
        alignItems: "center",
      },
    );
  const rows = m.respRows.map(([n, v]) => {
    const pts = Number(v.puntos || 0),
      occ = Math.round((pts / 6) * 100),
      vac = Number(m.vacDiasPorRecurso[n] || 0),
      disp = Math.max(0, Math.round(100 - (vac / m.habiles30) * 100));
    const note = vac
      ? `Vacaciones (${vac} d)`
      : pts > 6
        ? "Sobreasignado"
        : pts === 6
          ? "Ocupado 100%"
          : "Sin cambios";
    return h(
      "tr",
      "",
      cell(h("b", "", text(n))),
      cell(
        progress(
          occ,
          Math.min(100, occ),
          pts > 6 ? "#e23a4f" : pts === 6 ? "#f0a51c" : "#28ad69",
        ),
      ),
      cell(
        progress(
          disp,
          disp,
          disp < 70 ? "#e23a4f" : disp < 90 ? "#ef9d28" : "#28ad69",
        ),
      ),
      h("td", "aer-occ-note", note),
    );
  });
  const box = (label, value, cls = "") =>
    div(
      "box" + (cls ? " " + cls : ""),
      h("span", "", label),
      h("b", "", String(value)),
    );
  const resources = div(
    "aer-card",
    title(
      "Ocupación de recursos",
      "Capacidad actual y disponibilidad ajustada por vacaciones en los próximos 30 días.",
      m.recursosSobrecargados,
    ),
    div(
      "aer-effort-summary",
      box("Capacidad", m.capacidadTotal),
      box("Ocupada", m.puntosOcupados, "done"),
      box(
        "Alertas",
        m.recursosSobrecargados,
        m.recursosSobrecargados ? "alert" : "pending",
      ),
    ),
    styled(
      div(
        "",
        table(
          "aer-occ-table",
          [
            "Recurso",
            "Ocupación actual",
            "Capacidad próx. 30 días",
            "Observación",
          ],
          rows,
          "Sin recursos con esfuerzo asignado.",
        ),
      ),
      { overflow: "auto" },
    ),
  );
  const vacations = div(
    "aer-card",
    title(
      "Calendario de vacaciones",
      "Recursos ausentes por semana · próximas 6 semanas.",
    ),
    div(
      "aer-vac-week-grid",
      ...m.vacWeeks.map((w) =>
        div(
          `aer-vac-week ${w.count ? "" : "zero"}`,
          h("b", "", dateShort(w.ini)),
          h("span", "", String(w.count)),
        ),
      ),
    ),
    div(
      "aer-vac-upcoming",
      ...(m.vacacionesProximas.length
        ? m.vacacionesProximas
            .slice(0, 3)
            .map((v) =>
              div(
                "item",
                h(
                  "span",
                  "",
                  h("b", "", text(v.recurso)),
                  h("small", "", text(v.estado)),
                ),
                h("span", "date", `${dateText(v.inicio)} → ${dateText(v.fin)}`),
              ),
            )
        : [div("aer-sub", "Sin vacaciones próximas.")]),
    ),
  );
  return div("aer-plan-secondary", next, resources, vacations);
}

export function renderPlanning(target, m, filters, actions) {
  target.replaceChildren(
    div(
      "aer-plan-dashboard",
      div(
        "aer-plan-top-kpis",
        kpi("▣", "Compromisos", m.total, "Total del proyecto"),
        kpi(
          "✓",
          "Cerrados",
          m.cerrados,
          `${pct(m.pl.pctCerrados || m.avancePct)} del total`,
          "good",
        ),
        kpi(
          "◔",
          "Avance",
          m.avancePct + "%",
          `${m.atiempo} cerrados a tiempo`,
          "purple",
        ),
        kpi(
          "!",
          "Vencidos",
          m.vencidos,
          m.vencidos ? "requieren atención" : "sin vencidos",
          "bad",
        ),
        kpi(
          "◫",
          "Próximos 7 días",
          m.proximos7.length,
          "vencen pronto",
          "warn",
        ),
        kpi(
          "◇",
          "Hitos por validar",
          m.hitosValidar.length,
          "pendientes",
          "purple",
        ),
        kpi(
          "◷",
          "Ocupación",
          `${m.recursosOcupados}/${m.recursosConCap}`,
          m.recursosSobrecargados
            ? `${m.recursosSobrecargados} sobreasignado(s)`
            : `${m.puntosDisponibles} pts disponibles`,
          m.recursosSobrecargados ? "bad" : "purple",
        ),
        kpi(
          "⚑",
          "Vacaciones próximas",
          m.vacacionesProximas.length,
          "próx. 30 días",
          "good",
        ),
      ),
      div("aer-plan-main", timeline(m, actions), attention(m)),
      secondary(m),
      vacationTable(m, actions),
      activitiesTable(m, filters, actions),
    ),
  );
}
