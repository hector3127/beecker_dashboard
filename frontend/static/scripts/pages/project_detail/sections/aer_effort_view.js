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
import { hours, clamp } from "./aer_executive_model.js";

const pct = (n) => `${Math.round(Number(n || 0) * 10) / 10}%`;
const section = (name, hint) =>
  div(
    "aer-section-title",
    div("", h("h3", "", name), ...(hint ? [div("hint", hint)] : [])),
  );
const bar = (cls, width, background) =>
  div(
    cls,
    styled(h("i", ""), {
      width: width + "%",
      ...(background ? { background } : {}),
    }),
  );
const kpi = (icon, color, label, value, sub, width, background) =>
  div(
    "aer-vivid-card soft",
    div(
      "aer-vivid-kpi-head",
      h("span", `aer-vivid-icon ${color}`, icon),
      div(
        "",
        div("aer-vivid-label", label),
        div("aer-vivid-value", hours(value)),
        div("aer-vivid-sub", sub),
      ),
    ),
    bar("aer-vivid-bar", clamp(width), background),
  );

function recordTable(records, wide = false) {
  const headers = wide
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
  return table(
    "aer-vivid-table",
    headers,
    records.map((x) =>
      h(
        "tr",
        "",
        cell(dateText(x.fecha)),
        cell(text(x.recurso)),
        cell(text(x.actividad)),
        cell(text(x.descripcion)),
        ...(wide ? [cell(text(x.inicio || "")), cell(text(x.fin || ""))] : []),
        cell(`${x.duracion}h`),
        cell(x.billable ? "Facturable" : "No facturable"),
        cell(x.fueraHorario ? (wide ? "⚠ Fuera de horario" : "⚠") : "—"),
      ),
    ),
    wide
      ? "Sin registros en el rango seleccionado."
      : "Sin registros en este rango.",
  );
}

export function renderEffort(target, m, actions) {
  const {
    k,
    tasks,
    recursos,
    trend,
    regs,
    regsPreview,
    maxTask,
    maxMes,
    fact,
    noFact,
    outPct,
    totalPct,
    state,
  } = m;
  const range = (label, id, value) =>
    h("label", "", label, input(value, { id, type: "date" }));
  target.replaceChildren(
    div(
      "aer-vivid-grid",
      div(
        "aer-vivid-top",
        kpi(
          "◔",
          "purple",
          "Horas totales",
          k.horasTotales,
          `${pct(totalPct)} del plan`,
          totalPct,
          "linear-gradient(90deg,#7b43ea,#b285ff)",
        ),
        kpi(
          "▣",
          "blue",
          "Facturables",
          k.horasFacturables,
          pct(fact),
          fact,
          "linear-gradient(90deg,#3b1fd3,#813dff)",
        ),
        kpi(
          "◫",
          "pink",
          "No facturables",
          k.horasNoFacturables,
          pct(noFact),
          noFact,
          "linear-gradient(90deg,#ff43a4,#ff79c3)",
        ),
        kpi(
          "☾",
          "purple",
          "Fuera de horario",
          k.horasFueraHorario,
          pct(outPct),
          outPct,
          "linear-gradient(90deg,#612de1,#a78cff)",
        ),
      ),
      div(
        "aer-vivid-three",
        div(
          "aer-vivid-card",
          section(
            "Distribución por actividad",
            `Total: ${hours(k.horasTotales)}`,
          ),
          div(
            "aer-vivid-list",
            ...(tasks.length
              ? tasks.map((t) =>
                  div(
                    "aer-vivid-row",
                    div(
                      "txt",
                      h("b", "", text(t.nombre)),
                      bar(
                        "aer-vivid-progress",
                        (Number(t.horas || 0) / maxTask) * 100,
                      ),
                    ),
                    div("hrs", hours(t.horas)),
                  ),
                )
              : [div("aer-sub", "Sin horas registradas.")]),
          ),
        ),
        div(
          "aer-vivid-card",
          section("Tendencia de horas", "Evolución mensual del esfuerzo"),
          div(
            "aer-vivid-chart",
            ...(trend.length
              ? trend.map((v) =>
                  div(
                    "aer-vivid-col",
                    h("b", "", Number(v.horas || 0).toLocaleString("es-MX")),
                    styled(div("bar"), {
                      height:
                        Math.max(18, (Number(v.horas || 0) / maxMes) * 185) +
                        "px",
                    }),
                    h("small", "", text(v.mes)),
                  ),
                )
              : [h("span", "aer-sub", "Sin tendencia.")]),
          ),
        ),
        div(
          "aer-vivid-card",
          section("Facturables vs No facturables"),
          div(
            "aer-vivid-donut-wrap",
            styled(
              div(
                "aer-donut",
                div(
                  "",
                  h("b", "", hours(k.horasTotales).replace(" h", "")),
                  h("small", "", "horas totales"),
                ),
              ),
              {
                background: `conic-gradient(#5b2ad8 0 ${fact}%,#f4349b ${fact}% ${Math.min(100, fact + noFact)}%,#ece8f5 ${Math.min(100, fact + noFact)}% 100%)`,
              },
            ),
            div(
              "aer-vivid-legend",
              ...[
                ["Facturables", "#5b2ad8", k.horasFacturables, fact],
                ["No facturables", "#f4349b", k.horasNoFacturables, noFact],
              ].map(([name, color, value, percent]) =>
                div(
                  "row",
                  h(
                    "span",
                    "",
                    styled(h("i", "sw"), { background: color }),
                    name,
                  ),
                  h("b", "", hours(value)),
                  h("i", "", pct(percent)),
                ),
              ),
            ),
            div(
              "aer-vivid-note",
              fact >= 90
                ? "El porcentaje facturable del proyecto se mantiene alto."
                : "Existe una proporción relevante de horas no facturables que conviene revisar.",
            ),
          ),
        ),
      ),
      div(
        "aer-vivid-two",
        div(
          "aer-vivid-card",
          section("Detalle de consumo por recurso"),
          table(
            "aer-vivid-table",
            ["Recurso", "Hrs", "Fact.", "No fact.", "Fuera horario", "% total"],
            recursos.map((x) =>
              h(
                "tr",
                "",
                cell(
                  div(
                    "aer-name-cell",
                    h(
                      "span",
                      "aer-avatar-mini",
                      String(x.recurso || "?")
                        .split(/\s+/)
                        .map((s) => s[0])
                        .slice(0, 2)
                        .join("")
                        .toUpperCase(),
                    ),
                    div("nm", h("b", "", text(x.recurso))),
                  ),
                ),
                ...[
                  x.horasTotales,
                  x.facturables,
                  x.noFacturables,
                  x.fueraHorario,
                ].map((v) => cell(String(v))),
                cell(`${x.pctTotal}%`),
              ),
            ),
            "Sin datos.",
          ),
        ),
        div(
          "aer-vivid-card aer-clockify-preview",
          div(
            "aer-section-title",
            div(
              "",
              h("h3", "", "Detalle de registros (Clockify)"),
              div("hint", "Por default: semana en curso"),
            ),
            div(
              "aer-range-tools",
              range("Desde", "aer-clock-desde", state.desde),
              range("Hasta", "aer-clock-hasta", state.hasta),
              button(
                state.cargando ? "Consultando…" : "Aplicar",
                actions.query,
              ),
            ),
          ),
          recordTable(regsPreview),
          div(
            "aer-clockify-more",
            button(
              `Ver más (${regs.length})`,
              actions.openRecords,
              "aer-btn primary",
            ),
          ),
        ),
      ),
    ),
  );
}

export function openRecords(m) {
  document.getElementById("aer-modal-wide-back")?.remove();
  const back = el("div", {
    id: "aer-modal-wide-back",
    class: "aer-modal-wide-back",
  });
  const close = () => back.remove();
  back.addEventListener("click", (event) => {
    if (event.target === back) close();
  });
  back.append(
    div(
      "aer-modal-wide",
      styled(
        div(
          "",
          div(
            "",
            styled(h("h3", "", "Detalle de registros (Clockify)"), {
              margin: "0",
            }),
            div(
              "aer-sub",
              `${dateText(m.state.desde)} → ${dateText(m.state.hasta)} · ${m.regs.length} registros`,
            ),
          ),
          button("✕ Cerrar", close),
        ),
        {
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "12px",
          marginBottom: "12px",
        },
      ),
      styled(div("", recordTable(m.regs, true)), { overflow: "auto" }),
    ),
  );
  document.body.append(back);
  return back;
}
