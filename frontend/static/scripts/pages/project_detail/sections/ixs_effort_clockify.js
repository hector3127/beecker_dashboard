import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";
import { num, limit, dateText } from "./ixs_executive_model.js";
import { h, div, empty, heading } from "./ixs_executive_view.js";
import { activityRows, trendRows } from "./ixs_effort_model.js";

const b = (text) => h("b", "", text),
  small = (text) => h("small", "", text),
  span = (text) => h("span", "", text);
export const button = (text, action, cls = "ixs-btn", props = {}) =>
  el(
    "button",
    { class: cls, onclick: action, ...props },
    ...(Array.isArray(text) ? text : [text]),
  );
export function dateInput(id, label, value) {
  return h("label", "", label, el("input", { id, type: "date", value }));
}

/** Exact column variants of the original preview, full list and activity list. */
export function recordTable(records, mode = "preview") {
  const activity = mode === "activity",
    full = mode === "full";
  const headers = activity
    ? [
        "Fecha",
        "Descripción registrada",
        "Inicio",
        "Fin",
        "Duración",
        "Tipo",
        "Alerta",
      ]
    : full
      ? [
          "Fecha",
          "Recurso",
          "Actividad",
          "Descripción",
          "Inicio",
          "Fin",
          "Duración",
          "Tipo",
          "Alerta",
        ]
      : [
          "Fecha",
          "Recurso",
          "Actividad",
          "Descripción",
          "Duración",
          "Tipo",
          "Alerta",
        ];
  const td = (value) => h("td", "", value);
  const rows = records.map((x) =>
    h(
      "tr",
      "",
      td(dateText(x.fecha)),
      !activity ? [td(x.recurso ?? ""), td(x.actividad ?? "")] : null,
      h(
        "td",
        "description",
        activity ? x.descripcion || "Sin descripción" : (x.descripcion ?? ""),
      ),
      full || activity ? [td(x.inicio || "—"), td(x.fin || "—")] : null,
      td(activity ? b(num(x.duracion, 2) + " h") : num(x.duracion, 2) + " h"),
      td(x.billable ? "Facturable" : "No facturable"),
      td(x.fueraHorario === true ? "⚠ Fuera de horario" : "—"),
    ),
  );
  return div(
    "ixs-table-scroll",
    h(
      "table",
      `ixs-table${mode === "preview" ? " ixs-effort-records" : ""}`,
      h(
        "thead",
        "",
        h(
          "tr",
          "",
          headers.map((x) => h("th", "", x)),
        ),
      ),
      h(
        "tbody",
        "",
        rows.length
          ? rows
          : activity
            ? null
            : h(
                "tr",
                "",
                el(
                  "td",
                  { colspan: headers.length },
                  full
                    ? "Sin registros en el periodo."
                    : "Sin registros en el periodo seleccionado.",
                ),
              ),
      ),
    ),
  );
}

export function renderClockify(target, state, filtered, actions) {
  const regs = state.registros || [],
    content = (normal) =>
      state.cargando
        ? empty("Consultando Clockify…")
        : state.error
          ? empty(state.error)
          : normal;
  const activity = target.querySelector("#ixs-actividad-card"),
    chart = target.querySelector("#ixs-tendencia-card"),
    logs = target.querySelector("#ixs-registros-card");
  if (activity) {
    const rows = activityRows(regs),
      max = Math.max(1, ...rows.map((x) => x.horas)),
      total = regs.reduce((n, x) => n + Number(x.duracion || 0), 0);
    activity.replaceChildren(
      div(
        "ixs-section-head",
        div(
          "",
          h("h3", "", icon("list"), " Distribución por actividad"),
          small(
            "Despliega una actividad y abre las descripciones de cada recurso",
          ),
        ),
        small("Total: " + num(total, 2) + " h"),
      ),
      content(
        rows.length
          ? div(
              "ixs-effort-activity-list",
              rows.map((x, i) => {
                const bar = h("i", "");
                bar.style.width = limit((x.horas / max) * 100) + "%";
                return h(
                  "details",
                  "ixs-effort-activity",
                  h(
                    "summary",
                    "",
                    div(
                      "ixs-effort-task-top",
                      el("span", { class: "chev", "aria-hidden": "true" }, "▸"),
                      h("span", "name", x.nombre),
                      h("span", "hrs", num(x.horas, 2) + " h"),
                    ),
                    h(
                      "span",
                      "ixs-effort-task-sub",
                      `${x.personas.length} recurso(s) · ${x.registros} registro(s)`,
                    ),
                    div("ixs-effort-task-bar", bar),
                  ),
                  div(
                    "ixs-effort-members",
                    div(
                      "ixs-effort-member-head",
                      "Recurso · Horas registradas · Abrir descripciones",
                    ),
                    x.personas.map((r, j) =>
                      el(
                        "button",
                        {
                          type: "button",
                          class: "ixs-effort-member",
                          title: "Ver descripciones de " + r.nombre,
                          onclick: () => actions.activity(i, j),
                        },
                        h(
                          "span",
                          "avatar",
                          r.nombre
                            .trim()
                            .split(/\s+/)
                            .slice(0, 2)
                            .map((t) => t[0] || "")
                            .join("")
                            .toUpperCase(),
                        ),
                        h(
                          "span",
                          "person",
                          r.nombre,
                          small(
                            r.registros.length +
                              " registro(s) · Ver descripciones",
                          ),
                        ),
                        h("span", "time", num(r.horas, 2) + " h"),
                        el(
                          "span",
                          { class: "arrow", "aria-hidden": "true" },
                          "↗",
                        ),
                      ),
                    ),
                  ),
                );
              }),
            )
          : empty("Sin actividades."),
      ),
    );
  }
  if (chart) {
    const months = trendRows(regs),
      max = Math.max(1, ...months.map((x) => x.horas));
    chart.replaceChildren(
      heading(
        "chart",
        "Tendencia de horas",
        button(
          "Ver horas fuera de las estimadas",
          actions.excess,
          "ixs-btn primary",
        ),
      ),
      content(
        months.length
          ? div(
              "ixs-effort-trend",
              months.map((x) => {
                const bar = div("bar");
                bar.style.height = Math.max(3, (x.horas / max) * 100) + "%";
                return div("col", b(num(x.horas, 2)), bar, small(x.mes));
              }),
            )
          : empty("Sin meses registrados."),
      ),
    );
  }
  if (logs)
    logs.replaceChildren(
      heading(
        "clock",
        "Detalle de registros (Clockify)",
        small("Semana en curso por defecto"),
      ),
      div(
        "ixs-effort-range",
        dateInput("ixs-clock-desde", "Desde", state.desde),
        dateInput("ixs-clock-hasta", "Hasta", state.hasta),
        button("Aplicar", actions.filter),
      ),
      ...(state.cargando || state.error
        ? [content(null)]
        : [
            recordTable(filtered.slice(0, 5)),
            div(
              "ixs-effort-more",
              button(
                `Ver más (${filtered.length})`,
                actions.records,
                "ixs-btn primary",
              ),
            ),
          ]),
    );
}

function showModal(id, content, close, escape = false) {
  document.getElementById(id)?.remove();
  const modal = el("div", { id, class: "ixs-clockify-modal" }, content);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) close();
  });
  if (escape)
    modal.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });
  document.body.append(modal);
  return modal;
}
export function activityModal(task, person, close) {
  const records = person.registros
    .slice()
    .sort((a, b) =>
      (String(b.fecha || "") + " " + String(b.inicio || "")).localeCompare(
        String(a.fecha || "") + " " + String(a.inicio || ""),
      ),
    );
  const modal = showModal(
    "ixs-actividad-modal",
    el(
      "div",
      {
        class: "ixs-clockify-dialog ixs-activity-dialog",
        role: "dialog",
        "aria-modal": "true",
        "aria-label": "Descripciones de actividad",
      },
      div(
        "ixs-section-head",
        div(
          "",
          h("h3", "", icon("list"), " ", task.nombre),
          div(
            "ixs-activity-modal-info",
            b(person.nombre),
            h("span", "ixs-activity-modal-pill", num(person.horas, 2) + " h"),
            span(records.length + " registro(s)"),
          ),
        ),
        button("✕ Cerrar", close),
      ),
      recordTable(records, "activity"),
      div(
        "ixs-activity-modal-info",
        span("Actividad: " + task.nombre),
        span("·"),
        span("Recurso: " + person.nombre),
      ),
    ),
    close,
    true,
  );
  modal.querySelector("button")?.focus();
}
export function recordsModal(state, records, close) {
  showModal(
    "ixs-clockify-modal",
    el(
      "div",
      {
        class: "ixs-clockify-dialog",
        role: "dialog",
        "aria-modal": "true",
        "aria-label": "Registros Clockify",
      },
      div(
        "ixs-section-head",
        div(
          "",
          h("h3", "", icon("clock"), " Detalle de registros (Clockify)"),
          small(
            `${dateText(state.desde)} → ${dateText(state.hasta)} · ${records.length} registros`,
          ),
        ),
        button("✕ Cerrar", close),
      ),
      recordTable(records, "full"),
    ),
    close,
  );
}
