import {
  el,
  h,
  div,
  styled,
  button,
  input,
  table,
  cell,
  text,
  dateText,
} from "./aer_planning_dom.js";
import { stateClass } from "./actions_model.js";

const section = (name, hint, action) =>
  div(
    "aer-section-title",
    div("", h("h3", "", name), div("hint", hint)),
    ...(action ? [action] : []),
  );
const bar = (value, background) =>
  div("aer-bar", styled(h("i", ""), { width: value + "%", background }));
const kpi = (icon, cls, label, value, sub) =>
  div(
    "aer-vivid-card soft",
    div(
      "aer-vivid-kpi-head",
      h("span", `aer-vivid-icon ${cls}`, icon),
      div(
        "",
        div("aer-vivid-label", label),
        div("aer-vivid-value", String(value)),
        div("aer-vivid-sub", sub),
      ),
    ),
  );
const meta = (label, value) => div("blk", div("lbl", label), div("val", value));

export function renderRisks(target, m, actions) {
  const {
    k,
    ac,
    activos,
    crit,
    matrix,
    exposure,
    abiertosCnt,
    mitigCnt,
    cerrCnt,
    atencion,
    riesgoPct,
  } = m;
  const riskItems = activos.slice(0, 4).map((x) =>
    div(
      "aer-risk-item",
      div(
        "aer-risk-item-head",
        h("span", "aer-vivid-icon purple", "☰"),
        div(
          "aer-risk-item-title",
          h("b", "", text(x.riesgo)),
          h(
            "small",
            "",
            text(x.notas || "Riesgo en seguimiento del proyecto."),
          ),
        ),
        button("Ver detalle →", () => actions.open(x.uid)),
      ),
      div(
        "aer-risk-meta",
        meta(
          "Impacto",
          h("span", "aer-pill yellow", text(x.impacto || "Medio")),
        ),
        meta(
          "Probabilidad",
          h("span", "aer-pill yellow", text(x.probabilidad || "Media")),
        ),
        meta("Responsable", text(x.responsable || "—")),
        meta("Fecha compromiso", dateText(x.fechaLimite)),
      ),
      div(
        "aer-risk-plan",
        div(
          "txt",
          h("b", "", "Plan de mitigación"),
          h(
            "small",
            "",
            text(x.accion || "Definir acciones de mitigación y seguimiento."),
          ),
        ),
        div(
          "pct",
          bar(riesgoPct(x), "linear-gradient(90deg,#7b43ea,#a78cff)"),
          h("span", "", riesgoPct(x) + "%"),
        ),
      ),
    ),
  );
  const cells = ["Alta", "Media", "Baja"].flatMap((prob) => [
    div("axis", prob),
    ...["Bajo", "Medio", "Alto"].map((imp) => {
      const n = matrix[`${prob.toLowerCase()}|${imp.toLowerCase()}`] || 0,
        bg =
          prob === "Alta" && imp === "Alto"
            ? "#ffe0e4"
            : imp === "Alto" || prob === "Alta"
              ? "#fff1cf"
              : "#dff3e8";
      return styled(div("cell", n ? String(n) : ""), { background: bg });
    }),
  ]);
  const distribution = [
    ["Abiertos", abiertosCnt, "linear-gradient(90deg,#6c39e5,#8e63ef)"],
    ["En mitigación", mitigCnt, "linear-gradient(90deg,#f3a800,#ffca4d)"],
    ["Cerrados", cerrCnt, "linear-gradient(90deg,#20ad68,#66d38f)"],
  ].map(([name, count, color]) =>
    div(
      "row",
      div("meta", h("span", "", name), h("span", "", String(count))),
      bar(activos.length ? (count / activos.length) * 100 : 0, color),
    ),
  );
  const attention = div(
    "aer-risk-alert",
    div(
      "aer-risk-alert-head",
      styled(h("span", "aer-vivid-icon red", "!"), {
        width: "38px",
        height: "38px",
        fontSize: "17px",
      }),
      div(
        "",
        div("ttl", "Atención inmediata"),
        div("hint", "Acciones que requieren atención prioritaria"),
      ),
    ),
    atencion
      ? div(
          "aer-risk-alert-item",
          div(
            "main",
            h("b", "", text(atencion.accion || "Acción vencida")),
            h(
              "small",
              "",
              text(atencion.notas || "Requiere seguimiento inmediato."),
            ),
          ),
          div(
            "",
            div("lbl", "Responsable"),
            div("val", text(atencion.responsable || "—")),
          ),
          div(
            "",
            div("lbl", "Fecha compromiso"),
            div("val", dateText(atencion.fechaLimite)),
          ),
          h("span", "aer-pill purple", text(atencion.estado || "En progreso")),
        )
      : div("aer-sub", "Sin acciones vencidas en este momento."),
  );
  const rows = (ac.abiertas || []).slice(0, 8).map((x) => {
    const cls = stateClass(x.estado);
    return h(
      "tr",
      "",
      cell(text(x.accion)),
      cell(text(x.responsable)),
      cell(dateText(x.fechaLimite)),
      cell(
        h(
          "span",
          `aer-pill ${cls === "bad" ? "red" : cls === "ok" ? "green" : cls === "warn" ? "yellow" : "purple"}`,
          text(x.estado),
        ),
      ),
    );
  });
  target.replaceChildren(
    div(
      "aer-vivid-grid",
      div(
        "aer-risk-kpis",
        kpi(
          "♡",
          "green",
          "Health score",
          `${k.healthScore || 0}/100`,
          text(k.healthLabel || "Salud general"),
        ),
        kpi("◫", "blue", "Riesgos activos", activos.length, "abiertos"),
        kpi(
          "⚠",
          "red",
          "Críticos",
          crit.length,
          crit.length ? "requieren atención" : "sin críticos",
        ),
        kpi(
          "♧",
          "purple",
          "Alertas abiertas",
          m.alerts,
          "automáticas + manuales",
        ),
        kpi(
          "◷",
          "yellow",
          "Acciones vencidas",
          (ac.vencidas || []).length,
          "requieren atención",
        ),
        kpi(
          "◕",
          "blue",
          "Exposición general",
          exposure,
          "Nivel de riesgo del proyecto",
        ),
      ),
      div(
        "aer-risk-layout",
        div(
          "aer-vivid-card aer-risk-prioritized",
          section(
            "Riesgos priorizados",
            "Principales riesgos que requieren seguimiento",
            button("+ Riesgo", () => actions.open(), "aer-btn primary"),
          ),
          div(
            "aer-risk-stack",
            ...(riskItems.length
              ? riskItems
              : [div("aer-sub", "Sin riesgos activos.")]),
          ),
        ),
        div(
          "aer-risk-right",
          div(
            "aer-risk-right-top",
            div(
              "aer-vivid-card",
              section(
                "Matriz de riesgos (Probabilidad x Impacto)",
                "Distribución de riesgos activos",
              ),
              div(
                "aer-risk-matrix",
                div(""),
                div("head", "Bajo"),
                div("head", "Medio"),
                div("head", "Alto"),
                ...cells,
              ),
            ),
            div(
              "aer-vivid-card",
              section(
                "Distribución por estado",
                "Total de riesgos del proyecto",
              ),
              div("aer-risk-state-bars", ...distribution),
            ),
          ),
          attention,
        ),
      ),
      div(
        "aer-vivid-card",
        section(
          "Plan de acción / Seguimiento",
          "Acciones clave para la mitigación de riesgos",
          button("+ Nueva acción", actions.openAction, "aer-btn primary"),
        ),
        table(
          "aer-vivid-table",
          ["Acción", "Responsable", "Fecha compromiso", "Estado"],
          rows,
          "Sin acciones.",
        ),
      ),
    ),
  );
}

const field = (title, node, cls = "") => h("label", cls, title, node);
const select = (values, value, id) => {
  const node = el(
    "select",
    { id },
    ...values.map((v) => el("option", { selected: v === value }, v)),
  );
  return node;
};
export function openRisk(dashboard, uid, actions) {
  const x =
    (dashboard.riesgos?.filas || []).find((row) => row.uid === uid) || {};
  document.getElementById("aer-modal-back")?.remove();
  const back = el("div", { id: "aer-modal-back", class: "aer-modal-back" });
  const close = () => back.remove();
  back.addEventListener("click", (event) => {
    if (event.target === back) close();
  });
  const notes = el("textarea", { id: "ar-n" }, text(x.notas || ""));
  back.append(
    div(
      "aer-modal",
      styled(
        div(
          "",
          h("h3", "", (uid ? "Editar" : "Agregar") + " riesgo"),
          button("✕", close),
        ),
        { display: "flex", justifyContent: "space-between" },
      ),
      div(
        "aer-formgrid",
        field("Riesgo", input(x.riesgo || "", { id: "ar-r" }), "aer-span2"),
        field("Impacto", select(["Bajo", "Medio", "Alto"], x.impacto, "ar-i")),
        field(
          "Probabilidad",
          select(["Baja", "Media", "Alta"], x.probabilidad, "ar-p"),
        ),
        field("Responsable", input(x.responsable || "", { id: "ar-resp" })),
        field(
          "Fecha límite",
          input(x.fechaLimite || "", { type: "date", id: "ar-f" }),
        ),
        field("Estado", input(x.estado || "Abierto", { id: "ar-e" })),
        field(
          "Acción / mitigación",
          input(x.accion || "", { id: "ar-a" }),
          "aer-span2",
        ),
        field("Notas", notes, "aer-span2"),
      ),
      styled(
        div(
          "aer-actions",
          ...(uid ? [button("Eliminar", () => actions.remove(uid))] : []),
          button("Guardar", () => actions.save(uid), "aer-btn primary"),
        ),
        { marginTop: "12px" },
      ),
    ),
  );
  document.body.append(back);
  return back;
}
