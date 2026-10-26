import { el } from "#app/lib/dom.js";

const slot = (id) => el("div", { id });
const card = (...children) => el("div", { class: "card" }, ...children);
const heading = (text, props = {}) => el("h3", props, text);
const grid = (className, ...children) =>
  el("div", { class: "grid-3 " + className }, ...children);

export function mountGenericLayout(target, actions) {
  const head = (title, button, onclick, timeline = false) =>
    el(
      "div",
      { class: "gl-card-head" + (timeline ? " gl-timeline-head" : "") },
      heading(title, { class: "gl-card-title" }),
      el("button", { class: "btn gl-card-action", onclick }, button),
    );
  const summary = (icon, id, title, type) =>
    el(
      "div",
      {
        class: "gl-raid-summary gl-raid-" + type,
      },
      el("div", { class: "gl-raid-icon" }, icon),
      el("div", { class: "gl-raid-value", id }, "—"),
      el("div", { class: "gl-raid-label" }, title),
    );
  target.replaceChildren(
    slot("generic-header-placeholder"),
    slot("generic-kpis-placeholder"),
    grid(
      "gl-top-grid",
      card(
        head(
          "LÍNEA DE TIEMPO — HITOS PRINCIPALES",
          "+ Agregar Hito",
          actions.milestone,
          true,
        ),
        slot("generic-project-timeline"),
      ),
      card(
        heading("DISTRIBUCIÓN DEL AVANCE POR ÁREA"),
        slot("donut-area-ejecutivo"),
      ),
    ),
    slot("generic-resources-panel"),
    grid(
      "gl-hours-grid",
      card(
        heading("HORAS POR RECURSO", { class: "gl-hours-title" }),
        el("div", { id: "comparativo-recurso-mini", class: "gl-hours-chart" }),
      ),
      card(
        heading("HORAS POR ROL", { class: "gl-hours-title" }),
        el("div", { id: "comparativo-rol-mini", class: "gl-hours-chart" }),
      ),
    ),
    el(
      "div",
      { class: "grid-3 gl-top-grid", id: "grid-riesgos-raid" },
      card(
        head("⚠ RIESGOS CRÍTICOS (TOP 5)", "+ Agregar Riesgo", actions.risk),
        el(
          "div",
          {
            id: "riesgos-criticos-proyecto-azure",
            class: "loading gl-raid-loading",
          },
          "Cargando riesgos desde Azure...",
        ),
      ),
      card(
        heading("RAID RESUMEN"),
        el(
          "div",
          { class: "gl-raid-grid" },
          summary("🔴", "raid-proyecto-riesgos", "Riesgos Totales", "risks"),
          summary(
            "🟡",
            "raid-proyecto-pendientes",
            "Asuntos Pendientes",
            "pending",
          ),
          summary("💬", undefined, "Decisiones (sin fuente)", "decisions"),
          summary(
            "💡",
            "raid-proyecto-oportunidades",
            "Oportunidades",
            "opportunities",
          ),
        ),
      ),
    ),
    grid(
      "gl-bottom-grid",
      card(heading("HITOS DEL PROYECTO"), slot("generic-milestones-panel")),
      card(
        heading("HORAS CLOCKIFY — TASK / INVERSIÓN"),
        el(
          "div",
          {
            id: "clockify-task-hours-proyecto",
            class: "loading gl-tasks-loading",
          },
          "Cargando horas por task...",
        ),
      ),
    ),
  );
}
