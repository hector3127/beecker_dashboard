import { h, div, styled, button, input, text } from "./aer_planning_dom.js";

export function timeline(m, actions) {
  const {
    filas,
    grouped,
    pos,
    width,
    estadoCompromiso,
    fmtShort,
    monthMap,
    weeks,
    todayPos,
  } = m;
  const rows = grouped.flatMap((g) => [
    div("aer-gantt2-label group", text(g.responsable)),
    div("aer-gantt2-track aer-gantt2-grouptrack"),
    ...g.items.flatMap((x) => {
      const status = estadoCompromiso(x),
        check = input("", {
          class: "aer-commit-check",
          type: "checkbox",
          checked: status === "closed",
          "aria-label": `Marcar compromiso ${x.actividad} como cerrado`,
        });
      check.addEventListener("change", () =>
        actions.mark(x.uid, check.checked, check),
      );
      return [
        div(
          "aer-gantt2-label",
          div(
            "aer-commit-label",
            check,
            div(
              "",
              div("name", text(x.actividad)),
              div(
                "meta",
                h("span", `aer-status-dot ${status}`),
                `${x.estado || "Por iniciar"} · Compromiso: ${fmtShort(x.inicioPlan)} → ${fmtShort(x.finPlan)} · Esfuerzo: ${Number(x.esfuerzo || x.orden || 0)}`,
              ),
              ...(x.finReal
                ? [div("aer-close-date", `Cerrado: ${fmtShort(x.finReal)}`)]
                : []),
            ),
          ),
        ),
        div(
          "aer-gantt2-track",
          ...(x.inicioPlan && x.finPlan
            ? [
                styled(h("span", `aer-commit-line ${status}`), {
                  left: pos(x.inicioPlan) + "%",
                  width: width(x.inicioPlan, x.finPlan) + "%",
                }),
              ]
            : []),
          ...(x.finPlan
            ? [
                styled(h("span", "aer-commit-end"), {
                  left: pos(x.finPlan) + "%",
                }),
              ]
            : []),
          ...(String(x.tipo || "").toLowerCase() === "hito" && x.finPlan
            ? [
                styled(h("span", "aer-gantt2-hito"), {
                  left: pos(x.finPlan) + "%",
                }),
              ]
            : []),
        ),
      ];
    }),
  ]);
  const range = (name, value) => {
    const field = input(value, { type: "month" });
    field.addEventListener("change", () =>
      actions.rangeChange(name, field.value),
    );
    return h("label", "", name === "desde" ? "Desde " : "Hasta ", field);
  };
  return div(
    "aer-card",
    div(
      "aer-roadmap-toolbar",
      div(
        "",
        h("h3", "", "Roadmap de compromisos"),
        div(
          "aer-plan-side-note",
          "Visualiza el plan por responsable y su estado actual.",
        ),
      ),
      div(
        "aer-actions",
        div(
          "aer-plan-range",
          range("desde", m.fromMonth),
          range("hasta", m.toMonth),
        ),
        button(
          "+ Actividad / Hito",
          () => actions.openPlan(),
          "aer-btn primary",
        ),
        button("⇧ Cargar CSV", actions.openImport),
        ...(actions.communique
          ? [button("✉ Comunicados", actions.communique)]
          : []),
      ),
    ),
    div(
      "aer-gantt2",
      filas.length
        ? div(
            "aer-gantt2-wrap",
            ...(todayPos != null
              ? [
                  div(
                    "aer-gantt2-today-overlay",
                    styled(
                      div("aer-gantt2-today-global", h("span", "tag", "HOY")),
                      { left: todayPos + "%" },
                    ),
                  ),
                ]
              : []),
            div(
              "aer-gantt2-grid",
              div(""),
              div(
                "aer-gantt2-head",
                ...monthMap.map((v) =>
                  styled(div("aer-gantt2-month", v.label), {
                    left: v.center + "%",
                  }),
                ),
                ...weeks.map((v) =>
                  styled(
                    div(
                      "aer-gantt2-week",
                      h(
                        "span",
                        "aer-gantt2-week-label",
                        v.date.toLocaleDateString("es-MX", {
                          day: "numeric",
                          month: "short",
                        }),
                      ),
                    ),
                    { left: v.left + "%" },
                  ),
                ),
              ),
              ...rows,
            ),
            div(
              "aer-gantt2-legend",
              ...[
                ["Completado", "#25aa65"],
                ["En progreso", "#6c2ce0"],
                ["Por iniciar", "#d7d2e8"],
                ["Vencido", "#e23a4f"],
                ["Próximo a vencer", null, "duetoday"],
                ["Hito", null, "hito"],
                ["Por validar", null, "review"],
                ["Detenido", "#ef8d32"],
              ].map(([name, color, cls]) =>
                h(
                  "span",
                  "",
                  styled(h("i", cls || ""), color ? { background: color } : {}),
                  " " + name,
                ),
              ),
            ),
          )
        : div("aer-callout purple", "Aún no hay compromisos cargados."),
    ),
  );
}
