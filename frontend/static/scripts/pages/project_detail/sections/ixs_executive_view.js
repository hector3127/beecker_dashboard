import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";
import {
  executiveModel,
  timelineModel,
  num,
  pct,
  limit,
  dateText,
} from "./ixs_executive_model.js";

export const h = (tag, cls, ...children) =>
  el(
    tag,
    cls ? { class: cls } : {},
    ...children.flat(Infinity).filter((x) => x != null),
  );
export const div = (cls, ...children) => h("div", cls, ...children);
const b = (text) => h("b", "", text);
const small = (text) => h("small", "", text);
const span = (text) => h("span", "", text);
export const empty = (text) => div("ixs-empty", text);
const styled = (node, styles) => {
  Object.assign(node.style, styles);
  return node;
};
const money = (value) => "$" + num(value, 2);

function track(width, cls = "ixs-track", styles = {}) {
  return div(cls, styled(h("i", ""), { width: `${width}%`, ...styles }));
}
export function metric(label, value, text, color = "#6938da") {
  return div(
    "ixs-metric",
    span(label),
    track(limit(value), "ixs-track", { background: color }),
    b(text == null ? pct(value) : text),
  );
}
export function kpi(name, title, value, desc, percent, accent = "") {
  return div(
    "ixs-card ixs-kpi",
    div(
      "top",
      h("span", `ixs-icon ${accent}`, icon(name)),
      h("label", "", title),
    ),
    div("value", value),
    div("desc", desc || "\u00a0"),
    percent == null ? null : track(limit(percent), "track"),
  );
}
export function heading(name, text, right) {
  return div("ixs-section-head", h("h3", "", icon(name), " ", text), right);
}

export function timeline(data) {
  const m = timelineModel(data);
  if (!m) return empty("Sin fases disponibles en Historico_Proyectos.");
  const { plan, real, holds, markers, loneMarkers, min, max, range, pos } = m;
  function row(x) {
    const left = limit(pos(x.from)),
      right = limit(pos(x.to)),
      grouped = {};
    (x.markers || []).forEach((mark) => {
      const key = String(mark.time);
      (grouped[key] || (grouped[key] = [])).push(mark);
    });
    return div(
      "ixs-time-row",
      div(
        "ixs-time-label",
        x.name ?? "",
        x.active ? [" ", h("span", "ixs-badge", "En curso")] : null,
        small(`${dateText(x.from)} → ${dateText(x.to)}`),
      ),
      div(
        "ixs-time-track",
        styled(h("i", `ixs-time-bar ${x.type === "plan" ? "" : x.type}`), {
          left: `${left}%`,
          width: `${Math.max(0.6, right - left)}%`,
        }),
        (x.markers || []).map((mark) => {
          const same = grouped[String(mark.time)],
            offset = (same.indexOf(mark) - (same.length - 1) / 2) * 14;
          const node = el(
            "span",
            {
              class: `ixs-time-mark ${mark.cls}`,
              title: `${mark.label} · ${dateText(mark.date)}`,
              "aria-label": `${mark.label} · ${dateText(mark.date)}`,
            },
            mark.icon,
          );
          node.style.left = `clamp(10px,calc(${limit(pos(mark.time))}% + ${offset}px),calc(100% - 10px))`;
          return node;
        }),
      ),
    );
  }
  const months = [],
    first = new Date(min),
    end = new Date(max);
  for (
    let d = new Date(first.getFullYear(), first.getMonth(), 1), n = 0;
    d <= end && n < 30;
    d = new Date(d.getFullYear(), d.getMonth() + 1, 1), n++
  ) {
    const next = new Date(d.getFullYear(), d.getMonth() + 1, 1),
      a = Math.max(min, d.getTime()),
      z = Math.min(max, next.getTime());
    if (z <= a || ((z - a) / range) * 100 < 10) continue;
    const mid = (((a + z) / 2 - min) / range) * 100;
    months.push(
      styled(
        h(
          "span",
          "ixs-month-label",
          d
            .toLocaleDateString("es-MX", { month: "short", year: "2-digit" })
            .replace(/\./g, ""),
        ),
        { left: `${limit(mid)}%` },
      ),
    );
  }
  const seen = new Set(),
    legend = [];
  markers.forEach((mark) => {
    const key = mark.group + "|" + mark.icon;
    if (seen.has(key)) return;
    seen.add(key);
    legend.push(
      h(
        "span",
        "ixs-time-eventlegend",
        h("span", "ixs-time-chip", mark.icon),
        mark.group,
      ),
    );
  });
  const section = (label, rows) =>
    rows.length ? [div("ixs-time-section", label), rows.map(row)] : null;
  return div(
    "ixs-timeline",
    div(
      "ixs-timeline-core",
      div(
        "ixs-time-head",
        span(""),
        div("ixs-time-months ixs-exec-months", months),
      ),
      styled(h("i", "ixs-time-today-full"), {
        left: `calc(171px + (100% - 171px) * ${limit(pos(new Date())) / 100})`,
      }),
      section("Plan estimado (línea base)", plan),
      section("Ejecución real", real),
      section("Suspensiones", holds),
      loneMarkers.length
        ? [
            div("ixs-time-section", "Hitos adicionales"),
            row({
              name: "Eventos registrados",
              from: new Date(min),
              to: new Date(max),
              type: "events",
              markers: loneMarkers,
            }),
          ]
        : null,
      div(
        "ixs-legend",
        h("span", "", h("i", "ixs-exec-legend-plan"), "Planeación"),
        h("span", "", h("i", "ixs-exec-legend-real"), "Ejecución"),
        h("span", "", h("i", "ixs-exec-legend-hold"), "Suspendido"),
        legend,
        h("span", "ixs-time-today-tag", "┆ Hoy"),
      ),
    ),
  );
}

function area(data) {
  const vals = (data.distribucionArea || []).filter((x) => Number(x.horas) > 0),
    total = vals.reduce((a, v) => a + Number(v.horas || 0), 0);
  const colors = [
    "#5123bf",
    "#e52a84",
    "#8053ea",
    "#ef6bb0",
    "#8b8fda",
    "#32ab89",
    "#f6aa25",
  ];
  let acc = 0;
  const stops = vals
    .map((v, i) => {
      const start = acc;
      acc += (100 * Number(v.horas)) / total;
      return `${colors[i % colors.length]} ${start.toFixed(3)}% ${acc.toFixed(3)}%`;
    })
    .join(",");
  const donut = div(
    "ixs-donut",
    div("ixs-donut-center", b(num(total, 2)), small("HRS TOTALES")),
  );
  donut.style.background = stops ? "conic-gradient(" + stops + ")" : "#eceafb";
  const rows = vals.map((v, i) =>
    div(
      "ixs-area-row",
      styled(h("i", "sw"), { background: colors[i % colors.length] }),
      h("span", "name", v.nombre ?? ""),
      b(num(v.horas, 2) + " h"),
      small(pct(v.pct != null ? v.pct : total ? (100 * v.horas) / total : 0)),
    ),
  );
  const stat = (name, value, label) =>
    div("ixs-area-stat", icon(name), h("span", "", b(value), small(label)));
  return [
    div(
      "ixs-area-layout",
      donut,
      div("", rows.length ? rows : empty("Sin horas por área.")),
    ),
    div(
      "ixs-area-stats",
      stat("chart", vals.length, "Áreas"),
      stat(
        "people",
        (data.filasRecursosCompleto || []).filter((x) => x.nombre).length,
        "Recursos asignados",
      ),
      stat("clock", num(total, 2) + " h", "Registradas"),
    ),
  ];
}

export function balanceBadge(value) {
  if (value == null || value === "" || !Number.isFinite(Number(value)))
    return "—";
  const balance = Number(value),
    tone = balance < 0 ? "red" : balance === 0 ? "orange" : "green";
  const label =
    balance < 0
      ? "Horas excedidas"
      : balance === 0
        ? "Sin horas disponibles"
        : "Horas disponibles";
  return el(
    "span",
    {
      class: `ixs-badge ${tone} ixs-exec-balance`,
      title: label,
      "aria-label": `${label}: ${num(balance, 2)} horas`,
    },
    num(balance, 2),
  );
}
export function resourceTable(data) {
  const rows = data.filasRecursosCompleto || [],
    tot = data.totalesRecursos || {};
  const td = (value) => h("td", "", value),
    status = (value) =>
      /exced|retras/i.test(value)
        ? "red"
        : /riesgo/i.test(value)
          ? "orange"
          : "green";
  const body = rows.map((x) =>
    h(
      "tr",
      "",
      td(x.posicion ?? ""),
      el(
        "td",
        x.activo === false
          ? {
              class: "ixs-exec-inactive",
              title: "Recurso inactivo en el proyecto",
            }
          : {},
        x.nombre ?? "",
      ),
      td(x.banda || "—"),
      td(money(x.costingRate)),
      td(num(x.horasEstimadas, 2)),
      td(num(x.horasReales, 2)),
      td(num(x.horasNoFact, 2)),
      td(balanceBadge(x.balance)),
      td(pct(x.pctCumplimiento)),
      td(money(x.costoReal)),
      td(h("span", `ixs-badge ${status(x.estado)}`, x.estado || "—")),
    ),
  );
  return el(
    "div",
    { class: "ixs-table-scroll", "data-resource-workload": true },
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
            "Rol",
            "Recurso",
            "Banda",
            "Costing rate",
            "Estimadas",
            "Reales",
            "No fact.",
            "Balance",
            "% cumplimiento",
            "Costo real",
            "Estado",
          ].map((x) => h("th", "", x)),
        ),
      ),
      h(
        "tbody",
        "",
        body.length
          ? body
          : h("tr", "", el("td", { colspan: 11 }, "Sin recursos asignados.")),
      ),
      h(
        "tfoot",
        "",
        h(
          "tr",
          "",
          el("td", { colspan: 4 }, "Totales del proyecto"),
          td(num(tot.horasEstimadas, 2)),
          td(num(tot.horasReales, 2)),
          td(num(tot.horasNoFact, 2)),
          td(balanceBadge(tot.balance)),
          td(pct(tot.pctCumplimientoHoras)),
          td(money(tot.costoReal)),
          td(pct(tot.pctCumplimientoFinanciero) + " financiero"),
        ),
      ),
    ),
  );
}

export function miniHours(rows) {
  const data = (rows || [])
    .slice()
    .sort((a, b) => Number(b.horasReales || 0) - Number(a.horasReales || 0));
  const max = Math.max(
    1,
    ...data.map((x) =>
      Math.max(Number(x.horasReales || 0), Number(x.horasEstimadas || 0)),
    ),
  );
  const row = (x) =>
    div(
      "ixs-minirow",
      div(
        "top",
        span(x.nombre ?? ""),
        b(num(x.horasReales, 2) + " / " + num(x.horasEstimadas, 2) + " h"),
      ),
      track(limit((100 * Number(x.horasEstimadas || 0)) / max), "ixs-track", {
        background: "#cfd2e1",
      }),
      styled(track(limit((100 * Number(x.horasReales || 0)) / max)), {
        marginTop: "3px",
      }),
    );
  const result = data.slice(0, 5).map(row);
  if (data.length > 5) {
    const hidden = el(
      "div",
      { class: "ixs-more-rows", hidden: true },
      ...data.slice(5).map(row),
    );
    const text = `Ver todos (${data.length - 5} más) ↓`,
      button = el("button", { type: "button", class: "ixs-more-btn" }, text);
    button.addEventListener("click", () => {
      hidden.hidden = !hidden.hidden;
      button.textContent = hidden.hidden ? text : "Ver menos ↑";
    });
    result.push(div("ixs-more", hidden, button));
  }
  return result.length ? result : [empty("Sin información disponible.")];
}

function milestoneLists(m) {
  const detail = (title, subtitle) =>
    div("ixs-exec-flex", b(title ?? ""), small(subtitle));
  const chip = (x) =>
    el(
      "span",
      { class: "ixs-time-chip", title: x.group || "Hito adicional" },
      x.icon || "📌",
    );
  const pending = m.todo.map((x) =>
    div(
      "ixs-listrow",
      x.extra ? chip(x) : h("span", "ixs-icon", icon("calendar")),
      detail(x.name, `${x.state}${x.start ? " · " + dateText(x.start) : ""}`),
      h("span", "date", dateText(x.finish || x.start)),
    ),
  );
  const main = m.principalDone.map((x) =>
    div(
      "ixs-listrow",
      h("span", "ixs-icon green", icon("check")),
      detail(x.name, dateText(x.start) + " → " + dateText(x.finish)),
      h("span", "date", "✓"),
    ),
  );
  const extra = m.extrasDone.map((x) =>
    div(
      "ixs-listrow",
      chip(x),
      detail(x.name, (x.group || "Hito adicional") + " · " + dateText(x.start)),
      h("span", "date", "✓"),
    ),
  );
  return h(
    "section",
    "ixs-card",
    heading(
      "flag",
      "Hitos del proyecto",
      small(m.mainHitos.length + " eventos"),
    ),
    div("ixs-time-section", "Próximos / pendientes"),
    pending.length ? pending : empty("Sin hitos próximos."),
    div("ixs-time-section", "Fases completadas"),
    main.length ? main : empty("Sin fases completadas registradas."),
    div("ixs-time-section", "Demostraciones y pases realizados"),
    extra.length ? extra : empty("Sin hitos adicionales anteriores a hoy."),
  );
}

export function renderExecutive(target, data) {
  const m = executiveModel(data),
    { av, pr, rt } = m;
  const view = div(
    "ixs-exec-view",
    div(
      "ixs-kpis",
      kpi(
        "warning",
        "Estado general",
        m.state,
        m.riskGeneral ? "Requiere atención" : "Estado registrado en proyecto",
        null,
        m.riskGeneral ? "red" : "green",
      ),
      kpi(
        "target",
        "% avance",
        m.avanceDisponible ? pct(av.pct) : "—",
        m.avanceDisponible
          ? m.avancePorFechas
            ? `Estimado por etapa · Cerradas: ${m.done}/${m.totalMain}${av.etapaActualPct == null ? "" : " · En curso: " + pct(av.etapaActualPct)}`
            : `${m.avancePorHitos ? "Hitos: " + m.done + " de " + m.totalMain + " · " : ""}Planificado: ${av.pctTiempoTranscurrido == null ? "—" : pct(av.pctTiempoTranscurrido)}`
          : "Sin hitos principales",
        m.avanceDisponible ? av.pct : null,
      ),
      kpi(
        "chart",
        "Índice de ritmo",
        m.ritmoDisponible ? num(m.ritmo, 2) : "—",
        m.ritmoTexto,
        null,
        m.ritmo != null && m.avancePorHitos && m.ritmo < 0.9
          ? "red"
          : m.ritmo != null && !m.avancePorHitos && m.ritmo > 1.1
            ? "red"
            : m.ritmo != null && m.avancePorHitos && m.ritmo > 1.1
              ? "green"
              : "",
      ),
      kpi(
        "chart",
        "% cumpl. financiero",
        pct(m.financial),
        "Real vs estimado",
        m.financial,
        "green",
      ),
      kpi(
        "cash",
        "Presupuesto (hrs)",
        num(m.budget, 2),
        m.consumoDisponible
          ? `Gastado: ${num(m.burn, 2)} h · Resta: ${num(pr.etc, 2)} h`
          : "Sin registros de horas; consumo por verificar",
        m.consumoDisponible ? pr.pctEjecutado : null,
      ),
      kpi(
        "calendar",
        "Fecha de salida a PRD",
        m.fechaSalidaPRD ? dateText(m.fechaSalidaPRD) : "—",
        m.fechaSalidaPRD
          ? "Fin de Deployment"
          : "Sin fecha de fin de Deployment",
        null,
        m.riskHigh ? "red" : "",
      ),
    ),
    div(
      "ixs-main",
      h(
        "section",
        "ixs-card",
        heading(
          "layers",
          "Resumen ejecutivo",
          h("span", "ixs-badge", m.p.nombre || m.p.id),
        ),
        div(
          "ixs-summary",
          div(
            "",
            m.summaries.map((x) =>
              div(
                "ixs-sentence",
                h(
                  "span",
                  `dot ${x[0]}`,
                  x[0] === "red" ? "!" : x[0] === "amber" ? "!" : "✓",
                ),
                span(x[1]),
              ),
            ),
          ),
          div(
            "ixs-metrics",
            div(
              "ixs-note",
              icon("target"),
              " Indicadores del proyecto · datos del ejecutivo existente",
            ),
            metric("Tiempo", av.pctTiempoTranscurrido),
            metric(
              "Esfuerzo",
              rt.pctCumplimientoHoras,
              pct(rt.pctCumplimientoHoras),
              "#28ab70",
            ),
            metric(
              "Costo",
              m.financial,
              pct(m.financial),
              m.financial > 100 ? "#f0aa27" : "#28ab70",
            ),
            div(
              "ixs-metric",
              span("Riesgo"),
              el("div", {
                class: "ixs-track",
                title: "Sin puntuación numérica de riesgo en origen",
              }),
              b(m.riskDate),
            ),
            div(
              "ixs-note",
              b("Cumplimiento de hitos principales"),
              h("span", "ixs-exec-float", `${m.done} de ${m.totalMain}`),
              styled(track(m.totalMain ? (100 * m.done) / m.totalMain : 0), {
                margin: "6px 0",
              }),
              m.totalMain
                ? pct((100 * m.done) / m.totalMain) + " completados"
                : "Sin hitos principales registrados",
            ),
          ),
        ),
      ),
      h(
        "section",
        "ixs-card",
        heading("warning", "Atención ejecutiva", small("Indicadores actuales")),
        div(
          "ixs-attn",
          m.attention.map((a) =>
            div(
              `ixs-alert ${a.color}`,
              h("i", "dot"),
              div("ixs-exec-flex", b(a.title), h("p", "", a.desc)),
              h("span", `ixs-badge ${a.color}`, a.source),
            ),
          ),
        ),
      ),
    ),
    div(
      "ixs-grid2",
      h(
        "section",
        "ixs-card",
        heading("calendar", "Línea de tiempo — Hitos principales"),
        el("div", { id: "ixs-gantt-historico" }, timeline(data)),
      ),
      h(
        "section",
        "ixs-card",
        heading("donut", "Distribución del avance por área"),
        area(data),
      ),
    ),
    h(
      "section",
      "ixs-card ixs-exec-workload",
      heading(
        "people",
        "Carga de trabajo por recurso",
        small("Clockify + Recursos · datos existentes"),
      ),
      resourceTable(data),
    ),
    div(
      "ixs-grid3",
      h(
        "section",
        "ixs-card",
        heading("chart", "Horas por recurso"),
        miniHours(m.hoursRows),
      ),
      h(
        "section",
        "ixs-card",
        heading("chart", "Horas por rol"),
        miniHours(m.roleRows),
      ),
      div(
        "ixs-exec-raid-stack",
        h(
          "section",
          "ixs-card",
          heading("warning", "Riesgos críticos (Top 5)"),
          el(
            "div",
            { id: "ixs-risks-content", class: "ixs-empty" },
            "Consultando riesgos en Azure…",
          ),
        ),
        h(
          "section",
          "ixs-card",
          heading("layers", "RAID resumen"),
          div(
            "ixs-raid",
            div(
              "box ixs-exec-raid-risk",
              el("b", { id: "ixs-raid-risk" }, "—"),
              small("Riesgos"),
            ),
            div(
              "box ixs-exec-raid-issues",
              el("b", { id: "ixs-raid-issues" }, "—"),
              small("Asuntos pendientes"),
            ),
            div("box", b("—"), small("Decisiones (sin fuente)")),
            div(
              "box ixs-exec-raid-opps",
              el("b", { id: "ixs-raid-opps" }, "—"),
              small("Oportunidades"),
            ),
          ),
        ),
      ),
    ),
    div(
      "ixs-bottom",
      milestoneLists(m),
      h(
        "section",
        "ixs-card",
        heading("clock", "Horas Clockify — Task / inversión"),
        el(
          "div",
          { id: "ixs-tasks-content", class: "ixs-empty" },
          "Consultando horas por task…",
        ),
      ),
    ),
  );
  // No extra layout box: the previous executive has sibling sections.
  target.replaceChildren(...view.childNodes);
  target.dataset.renderer = "modular";
}

export function renderRaid(target, result) {
  if (!result || !result.ok) {
    target.textContent = result?.error
      ? "Azure: " + result.error
      : "Riesgos no disponibles";
    return;
  }
  const seen = new Set(),
    rows = (result.riesgos || [])
      .filter((x) => {
        const key = String(x.id || x.descripcion || "");
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .slice(0, 5);
  target.replaceChildren(
    ...(rows.length
      ? rows.map((x) =>
          div(
            "ixs-listrow",
            h("span", "ixs-icon red", icon("warning")),
            div(
              "",
              b(x.descripcion ?? ""),
              small(`${x.impacto || ""} · ${x.estado || ""}`),
            ),
          ),
        )
      : [empty("Sin riesgos Active / Proposed en Azure.")]),
  );
  [
    ["ixs-raid-risk", result.totalRiesgos],
    ["ixs-raid-issues", result.totalPendientes],
    ["ixs-raid-opps", result.totalOportunidades],
  ].forEach(([id, value]) => {
    const node = target.closest("#ixs-tab-contenido").querySelector("#" + id);
    if (node) node.textContent = String(value == null ? "—" : value);
  });
}
export function renderTasks(target, result) {
  if (!result || !result.ok) {
    target.textContent = "No disponibles: " + (result?.error || "Clockify");
    return;
  }
  const tasks = (result.tasks || []).filter((x) => Number(x.horas) > 0);
  target.replaceChildren(
    div(
      "ixs-raid",
      div("box", b(num(result.invOperativa, 2) + " h"), small("INV_OPERATIVA")),
      div(
        "box ixs-exec-commercial",
        b(num(result.invComercial, 2) + " h"),
        small("INV_COMERCIAL"),
      ),
    ),
    div(
      "ixs-minirow ixs-exec-task-title",
      `Horas por task · ${result.nomenclatura || ""} `,
      h("span", "ixs-exec-float", num(result.totalHoras, 2) + " h"),
    ),
    ...(result.rango?.fechaInicio && result.rango?.fechaFin
      ? [
          div(
            "ixs-exec-task-range",
            `Rango: ${String(result.rango.fechaInicio).slice(0, 10)} → ${String(result.rango.fechaFin).slice(0, 10)} · Tasks activas`,
          ),
        ]
      : []),
    div(
      "ixs-exec-task-scroll",
      tasks.length
        ? tasks.map((x) =>
            div(
              "ixs-listrow",
              h("span", "ixs-exec-task-name", x.nombre ?? ""),
              b(num(x.horas, 2) + " h"),
            ),
          )
        : empty("Sin tasks con horas."),
    ),
  );
}
