// @ts-check
import { el } from "#app/lib/dom.js";
import {
  executiveModel,
  hours,
  formatDate,
  clamp,
} from "./aer_executive_model.js";

const h = (tag, cls, ...children) =>
  el(
    tag,
    cls ? { class: cls } : {},
    ...children
      .flat(Infinity)
      .filter((value) => value != null && value !== false),
  );
const div = (cls, ...children) => h("div", cls, ...children);
const bold = (value) => h("b", "", value);
const span = (value) => h("span", "", value);
const empty = (text) => div("aer-exec-empty", text);
const tone = (value) =>
  value >= 80 ? "#20ad68" : value >= 60 ? "#f3a800" : "#e7354f";

function progress(value, cls = "aer-bar", color = "") {
  const fill = h("i", "");
  fill.style.width = `${clamp(value)}%`;
  if (color) fill.style.background = color;
  return div(cls, fill);
}

function metric(label, value, color, text) {
  return div(
    "aer-exec-metric-row",
    div("aer-exec-metric-head", bold(label), span(text)),
    progress(value, "aer-bar", color),
  );
}

function kpi(cls, icon, label, value, sub, pct) {
  return div(
    `aer-exec-kpi ${cls}`,
    div("row", h("span", "icon", icon), h("span", "label", label)),
    div("value", value),
    div("sub", sub || ""),
    pct == null ? null : progress(pct, "bar"),
  );
}

function summaryPoints(m) {
  const points = [];
  const push = (cls, ...message) =>
    points.push(
      div(
        `aer-exec-point ${cls}`,
        h("span", "ico", cls === "ok" ? "✓" : cls === "warn" ? "!" : "•"),
        div("txt", ...message),
      ),
    );
  const { healthScore, k, vencidos, vencenHoy, nextMilestone, criticos } = m;
  if (healthScore >= 85)
    push(
      "ok",
      "El proyecto mantiene una salud general ",
      bold(k.healthLabel || "saludable"),
      ", con avance parcial y control favorable del costo.",
    );
  else if (healthScore >= 70)
    push(
      "warn",
      "La salud general se mantiene en un nivel ",
      bold("estable"),
      ", aunque ya existen puntos que requieren seguimiento ejecutivo.",
    );
  else
    push(
      "bad",
      "La salud general del proyecto está en un nivel de ",
      bold("alerta"),
      ". Conviene revisar compromisos, riesgos y consumo.",
    );
  if (vencidos > 0)
    push(
      "warn",
      `Existe${vencidos === 1 ? "" : "n"} `,
      bold(
        `${vencidos} compromiso${vencidos === 1 ? "" : "s"} vencido${vencidos === 1 ? "" : "s"}`,
      ),
      ` que requiere${vencidos === 1 ? "" : "n"} seguimiento inmediato.`,
    );
  else if (vencenHoy > 0)
    push(
      "warn",
      "Hoy vencen ",
      bold(`${vencenHoy} compromiso${vencenHoy === 1 ? "" : "s"}`),
      "; conviene confirmar cierre o replanear con el responsable.",
    );
  else
    push(
      "ok",
      "No se observan compromisos vencidos al día de hoy y el seguimiento temporal permanece controlado.",
    );
  if (nextMilestone)
    push(
      "ok",
      "El próximo compromiso relevante es ",
      bold(nextMilestone.actividad),
      ", con fecha ",
      bold(formatDate(nextMilestone.finPlan)),
      ".",
    );
  else
    push(
      "ok",
      "No hay próximos hitos registrados dentro del rango visible del proyecto.",
    );
  if (criticos > 0)
    push(
      "bad",
      `Se identific${criticos === 1 ? "a" : "an"} `,
      bold(`${criticos} riesgo${criticos === 1 ? " crítico" : "s críticos"}`),
      " que conviene monitorear en comité.",
    );
  else
    push(
      "ok",
      "No se observan riesgos críticos ni bloqueos relevantes en este momento.",
    );
  return div("aer-exec-points", points);
}

function metrics(m) {
  const {
    dims,
    tiempoVsPlan,
    cerrados,
    total,
    pctATiempo,
    pctCerrados,
    vencidos,
  } = m;
  return div(
    "aer-exec-metrics",
    div("aer-exec-chip", `◉ ${m.badgeText}`),
    metric(
      "Tiempo",
      tiempoVsPlan,
      tiempoVsPlan >= 80
        ? "#f3a800"
        : tiempoVsPlan >= 60
          ? "#f0b22a"
          : "#e94359",
      `${tiempoVsPlan}%`,
    ),
    ...[
      ["Esfuerzo", dims.esfuerzo],
      ["Costo", dims.costo],
      ["Riesgo", dims.riesgo],
    ].map(([label, value]) =>
      metric(
        label,
        value == null ? 0 : value,
        tone(value),
        value == null ? "N/D" : `${Math.round(value)}%`,
      ),
    ),
    div(
      "aer-exec-commit",
      div(
        "top",
        bold("Cumplimiento de compromisos"),
        span(`${cerrados} de ${total || 0}`),
      ),
      progress(
        pctATiempo || pctCerrados,
        "aer-bar",
        "linear-gradient(90deg,#5a2bd7,#8e57ec)",
      ),
      div(
        "meta",
        span(`${Math.round(pctATiempo || pctCerrados)}% cerrados a tiempo`),
        bold(`${vencidos} vencido(s)`),
      ),
    ),
  );
}

function tabLink(text, tab, navigate) {
  const link = el(
    "a",
    { href: "#aer-tab-content", class: "aer-exec-attn-link" },
    text,
  );
  link.addEventListener("click", (event) => {
    event.preventDefault();
    navigate(tab);
  });
  return link;
}

function attention(m, navigate) {
  return div(
    "aer-card",
    div(
      "aer-exec-attn-head",
      h("h3", "", "Atención ejecutiva"),
      tabLink("Ver todas las acciones →", "acciones", navigate),
    ),
    div(
      "aer-exec-attn",
      m.attn
        .slice(0, 4)
        .map((x) =>
          div(
            `aer-exec-alert ${x.cls}`,
            h("span", "dot"),
            div(
              "txt",
              bold(x.title),
              h("small", "", x.detail || ""),
              div(
                "meta",
                span(`👤 ${x.responsable || "—"}`),
                x.fecha ? span(`📅 ${formatDate(x.fecha)}`) : null,
              ),
            ),
            h(
              "span",
              `pill ${x.cls === "purple" ? "pill-purple" : ""}`,
              x.source,
            ),
          ),
        ),
    ),
  );
}

function cardTitle(text, tab, navigate) {
  return div(
    "aer-card-title-row",
    div("", h("h3", "", text)),
    tab ? tabLink("Ver todos →", tab, navigate) : null,
  );
}

function upcoming(m, navigate) {
  const rows = m.upcomingCombined
    .slice(0, 5)
    .map((x) =>
      div(
        "row",
        h("span", `dot aer-exec-dot-${x.tipo}`),
        div(
          "txt",
          bold(x.titulo),
          h("small", "", x.responsable || "Sin responsable"),
          x.tag ? h("span", "aer-exec-tag", x.tag) : null,
        ),
        h("span", "date", formatDate(x.fecha)),
      ),
    );
  return div(
    "aer-card",
    cardTitle("Próximos hitos / decisiones (30 días)", "planeacion", navigate),
    div(
      "aer-exec-list",
      rows.length ? rows : empty("Sin compromisos o acciones próximas."),
    ),
  );
}

function finances(m) {
  const { k, costoReal, presupuestoPct } = m;
  const donut = div(
    "aer-donut",
    div(
      "",
      bold(hours(k.horasTotales).replace(" h", "")),
      h("small", "", "consumo"),
    ),
  );
  donut.style.background = `conic-gradient(#5a2bd7 0 ${presupuestoPct}%,#e8e5f2 ${presupuestoPct}% 100%)`;
  const rows = [
    ["consumo", "Consumo", hours(k.horasTotales)],
    ["facturables", "Facturables", hours(k.horasFacturables)],
    ["no-facturables", "No facturables", hours(k.horasNoFacturables)],
    ["fuera-horario", "Fuera de horario", hours(k.horasFueraHorario)],
    ["costo", "Costo real", `$${costoReal.toLocaleString("es-MX")}`],
  ];
  return div(
    "aer-card",
    cardTitle("Finanzas y esfuerzo"),
    div(
      "aer-exec-fin-wrap",
      donut,
      div(
        "aer-exec-fin-legend",
        rows.map(([cls, label, value]) =>
          div(
            "mini",
            h("span", "", h("i", `sw aer-exec-swatch-${cls}`), label),
            h("span", "v", value),
          ),
        ),
      ),
    ),
  );
}

function dependencies(m, navigate) {
  const rows = m.depUnique
    .filter((x) => x.status !== "Resuelta")
    .slice(0, 3)
    .map((g) => {
      const x = g.rows[0],
        cls =
          g.status === "Vencida"
            ? "bad"
            : g.status === "Detenida"
              ? "warn"
              : "info";
      return div(
        "aer-exec-dep-item",
        div(
          "txt",
          bold(g.dependencia),
          h(
            "small",
            "",
            `${x.actividad ?? ""}${g.rows.length > 1 ? ` · ${g.rows.length} actividades` : ""}`,
          ),
        ),
        h("span", `aer-badge ${cls}`, g.status),
      );
    });
  const stat = (cls, value, text) => div(`box ${cls}`, bold(value), span(text));
  return div(
    "aer-card",
    cardTitle("Riesgos y dependencias", "riesgos", navigate),
    div(
      "aer-exec-stats",
      stat("red", m.criticos, "riesgo crítico"),
      stat(
        "blue",
        m.depVencidas + m.depAbiertas + m.depDetenidas,
        "dependencias clave",
      ),
      stat("green", m.bloqueos, "bloqueos críticos"),
    ),
    div(
      "aer-exec-dep-list",
      rows.length
        ? rows
        : empty("Sin dependencias abiertas, detenidas o vencidas."),
    ),
  );
}

/** Safe DOM entry; the existing controller still owns navigation to other tabs. */
export function renderAerExecutive(target, data, navigate, now = new Date()) {
  const m = executiveModel(data, now);
  const {
    k,
    healthScore,
    pctCerrados,
    cerrados,
    total,
    tiempoVsPlan,
    durationPct,
    presupuestoPct,
    costoReal,
    criticos,
    abiertosRiesgo,
    nextMilestone,
    nextMilestoneDate,
    nextMilestoneCount,
  } = m;
  const view = div(
    "aer-exec-view",
    div(
      "aer-exec-top",
      kpi(
        "health",
        "♡",
        "Health Score",
        `${healthScore}/100`,
        k.healthLabel || "—",
        healthScore,
      ),
      kpi(
        "progress",
        "▥",
        "Avance global",
        `${Math.round(pctCerrados)}%`,
        `${cerrados} de ${total} compromisos cerrados`,
        pctCerrados,
      ),
      kpi(
        "time",
        "◔",
        "Tiempo vs plan",
        `${tiempoVsPlan}%`,
        durationPct == null
          ? "sin periodo base"
          : `${Math.round(durationPct)}% del periodo transcurrido`,
        tiempoVsPlan,
      ),
      kpi(
        "budget",
        "◉",
        "Presupuesto consumido",
        `${Math.round(presupuestoPct * 10) / 10}%`,
        `${hours(k.horasTotales)} registradas`,
        presupuestoPct,
      ),
      kpi(
        "cost",
        "$",
        "Costo real",
        `$${costoReal.toLocaleString("es-MX")}`,
        "según costing rate",
        null,
      ),
      kpi(
        `risk ${criticos ? "" : "aer-exec-no-risk"}`,
        "⚠",
        "Riesgos críticos",
        String(criticos),
        `${abiertosRiesgo} riesgo(s) activos`,
        criticos ? 100 : 0,
      ),
      kpi(
        "next",
        "⚑",
        "Próximo hito",
        nextMilestoneDate ? formatDate(nextMilestoneDate) : "—",
        nextMilestone
          ? `${nextMilestoneCount} eventos próximos`
          : "sin eventos próximos",
        null,
      ),
    ),
    div(
      "aer-exec-main",
      div(
        "aer-card",
        h("h3", "aer-exec-summary-title", "Resumen ejecutivo"),
        div("aer-exec-summary", summaryPoints(m), metrics(m)),
      ),
      attention(m, navigate),
    ),
    div(
      "aer-exec-grid3",
      upcoming(m, navigate),
      finances(m),
      dependencies(m, navigate),
    ),
  );
  view.dataset.renderer = "modular";
  target.replaceChildren(view);
}
