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
import { PLAN_STATES } from "./aer_planning_model.js";
import { normalize } from "./actions_model.js";

export function vacationTable(m, actions) {
  return div(
    "aer-card",
    div(
      "aer-plan-table-head",
      div(
        "",
        h("h3", "", "Registros de vacaciones"),
        div("sub", "Vacaciones registradas para el proyecto."),
      ),
      button(
        "+ Registrar vacaciones",
        () => actions.openVacation(),
        "aer-btn primary",
      ),
    ),
    styled(
      div(
        "",
        table(
          "aer-vac-table",
          [
            "Recurso",
            "Inicio",
            "Fin",
            "Días",
            "Estado",
            "Comentarios",
            "Registrado por",
            "Editar",
          ],
          m.vacaciones.map((v) => {
            const s = normalize(v.estado),
              cls = /cancel|rechaz/.test(s)
                ? "cancel"
                : /pend/.test(s)
                  ? "pending"
                  : "";
            return h(
              "tr",
              "",
              cell(h("b", "", text(v.recurso))),
              cell(dateText(v.inicio)),
              cell(dateText(v.fin)),
              cell(String(v.dias)),
              cell(h("span", `aer-vac-pill ${cls}`, text(v.estado))),
              cell(text(v.comentarios || "—")),
              cell(text(v.registradoPor || "—")),
              cell(button("✎", () => actions.openVacation(v.uid))),
            );
          }),
          "Sin vacaciones registradas.",
        ),
      ),
      { overflow: "auto" },
    ),
  );
}

export function activitiesTable(m, filters, actions) {
  const search = input(filters.actividad || "", {
    placeholder: "Buscar actividad…",
  });
  search.addEventListener("input", () =>
    actions.filterSet("actividad", search.value),
  );
  const all = input("", {
    id: "aer-plan-select-all",
    class: "aer-plan-select",
    type: "checkbox",
  });
  all.addEventListener("change", () => actions.toggleAll(all.checked));
  const active = (field) =>
    field === "compromiso"
      ? filters.compromisoDesde || filters.compromisoHasta
      : field === "cierre"
        ? filters.cierreDesde || filters.cierreHasta
        : filters[field];
  const header = (name, field) => {
    const control = button(
      "⌄",
      (e) => actions.openFilter(e, field),
      `aer-plan-filter-btn ${active(field) ? "active" : ""}`,
    );
    if (active(field)) control.append(h("span", "aer-plan-filter-dot"));
    return h("th", "aer-plan-header", div("lbl", name + " ", control));
  };
  const rows = m.filas.map((x) => {
    const selected = input(x.uid, {
      class: "aer-plan-select aer-plan-row-check",
      type: "checkbox",
    });
    selected.addEventListener("change", actions.selection);
    const state = el(
      "select",
      { id: `apt-est-${x.uid}`, class: "aer-plan-table-select" },
      ...PLAN_STATES.map((v) =>
        el(
          "option",
          { value: v, selected: v === (x.estado || "Por iniciar") },
          v,
        ),
      ),
    );
    state.addEventListener("change", () => actions.inlineState(x.uid));
    const end = input(x.finReal || "", {
      id: `apt-close-${x.uid}`,
      type: "date",
      class: "aer-plan-table-input",
      disabled: x.estado !== "Completado",
    });
    end.addEventListener("change", () => actions.inlineState(x.uid));
    const dep = m.depStatus(x),
      depClass =
        dep === "Vencida"
          ? "bad"
          : dep === "Detenida"
            ? "warn"
            : dep === "Resuelta"
              ? "ok"
              : "info";
    return el(
      "tr",
      {
        dataset: {
          planRow: x.uid,
          tipo: x.tipo || "",
          actividad: x.actividad || "",
          responsable: x.responsable || "Sin responsable",
          compromiso: x.finPlan || "",
          estado: x.estado || "Por iniciar",
          cierre: x.finReal || "",
        },
      },
      cell(selected),
      cell(
        (String(x.tipo || "").toLowerCase() === "hito" ? "◇ " : "") +
          text(x.tipo),
      ),
      cell(text(x.actividad)),
      cell(text(x.responsable)),
      cell(`${dateText(x.inicioPlan)} → ${dateText(x.finPlan)}`),
      cell(state),
      cell(end),
      cell(
        x.dependencia
          ? div(
              "",
              h("b", "", text(x.dependencia)),
              h("br", ""),
              h("span", `aer-badge ${depClass}`, dep),
            )
          : "—",
      ),
      cell(
        h(
          "b",
          "",
          String(Number(x.esfuerzo != null ? x.esfuerzo : x.orden || 0)),
        ),
      ),
      cell(
        styled(
          button("✎", () => actions.openPlan(x.uid), "aer-btn", {
            type: "button",
            title: "Editar actividad completa",
          }),
          { padding: "5px 8px", fontSize: "14px" },
        ),
        el(
          "span",
          {
            id: `apt-save-${x.uid}`,
            class: "aer-autosave-state",
            style: { display: "none" },
          },
          "—",
        ),
      ),
    );
  });
  const body = el(
    "tbody",
    { id: "aer-plan-table-body" },
    ...(rows.length
      ? rows
      : [h("tr", "", el("td", { colspan: 10 }, "Sin datos."))]),
  );
  return div(
    "aer-card",
    div(
      "aer-plan-table-head",
      div(
        "",
        h("h3", "", "Actividades / Entregables"),
        div("sub", "Listado de actividades, hitos y entregables del proyecto."),
      ),
      div(
        "aer-actions",
        h("label", "aer-plan-search", "⌕ ", search),
        button("⌄ Filtros", (e) => actions.openFilter(e, "estado")),
      ),
    ),
    div(
      "aer-plan-bulkbar",
      styled(
        div(
          "",
          all,
          el(
            "label",
            {
              for: "aer-plan-select-all",
              style: { fontSize: "10px", fontWeight: "700", cursor: "pointer" },
            },
            "Seleccionar todas",
          ),
          el(
            "span",
            { id: "aer-plan-selected-count", class: "count" },
            "0 seleccionadas",
          ),
          button("🗑 Eliminar", actions.removeSelected, "aer-btn danger", {
            id: "aer-plan-delete-selected",
            disabled: true,
          }),
        ),
        { display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" },
      ),
      div(
        "aer-plan-filter-tools",
        el("span", {
          id: "aer-plan-filter-count",
          class: "aer-plan-filter-count",
        }),
        button(
          "Limpiar filtros",
          actions.clearFilters,
          "aer-btn aer-plan-filter-clear",
          { type: "button" },
        ),
      ),
    ),
    styled(
      div(
        "",
        h(
          "table",
          "aer-table plan-pretty",
          h(
            "thead",
            "",
            h(
              "tr",
              "",
              styled(h("th", ""), { width: "34px" }),
              header("Tipo", "tipo"),
              header("Actividad", "actividad"),
              header("Responsable", "responsable"),
              header("Compromiso", "compromiso"),
              header("Estado", "estado"),
              header("Fecha de cierre", "cierre"),
              h("th", "aer-plan-header", div("lbl", "Dependencia")),
              h("th", "aer-plan-header", div("lbl", "Esfuerzo")),
              styled(h("th", "aer-plan-header", div("lbl", "Editar")), {
                width: "54px",
              }),
            ),
          ),
          body,
        ),
      ),
      { overflow: "auto" },
    ),
  );
}
