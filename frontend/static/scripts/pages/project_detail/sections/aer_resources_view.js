import { svg } from "#app/lib/dom.js";
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
import { resources } from "./aer_planning_model.js";
import { category, categoryClass } from "./aer_resources_model.js";

const section = (title, hint) =>
  div(
    "aer-section-title",
    hint === undefined
      ? h("h3", "", title)
      : div("", h("h3", "", title), div("hint", hint)),
  );
const card = (...nodes) => div("aer-vivid-card", ...nodes);
const empty = (label) => div("aer-sub", label);
const pill = (x) =>
  h("span", `aer-pill ${categoryClass(x.score)}`, category(x.score));
const scoreCell = (value) => h("td", "score", `${value}/100`);
const initials = (value) =>
  value
    .split(/\s+/)
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

export function renderResources(target, m, dashboard, actions) {
  const {
    evOrdenadas,
    recursos,
    selected,
    latest,
    avg,
    pendientes,
    observacion,
    top,
    sel,
    pts,
    xs,
    ys,
    poly,
    ptsDelta,
    cats,
    a1,
    a2,
    a3,
    prox,
    strengths,
  } = m;
  const select = el(
    "select",
    {
      class: "aer-eval-select",
      onchange: (e) => actions.select(e.target.value),
    },
    ...recursos.map((n) =>
      el("option", { value: n, selected: n === selected }, n),
    ),
  );
  const chart = div("aer-eval-chart");
  if (pts.length)
    chart.append(
      svg(
        "svg",
        {
          viewBox: "0 0 100 100",
          preserveAspectRatio: "xMidYMid meet",
          "data-evaluation-points": poly,
          role: "img",
          "aria-label": `Histórico de evaluaciones: ${pts.map((x) => x.score).join(", ")}`,
        },
        svg("polyline", {
          points: poly,
          fill: "none",
          stroke: "#6b32df",
          "stroke-width": 1.5,
          "vector-effect": "non-scaling-stroke",
        }),
        ...pts.flatMap((x, i) => [
          svg("circle", {
            cx: xs[i],
            cy: ys[i],
            r: 2.2,
            fill: "#6b32df",
            "vector-effect": "non-scaling-stroke",
          }),
          svg(
            "text",
            {
              x: xs[i],
              y: ys[i] - 5,
              "text-anchor": "middle",
              "font-size": 4,
              fill: "#251d58",
            },
            String(x.score),
          ),
        ]),
      ),
    );
  else chart.append(empty("Sin histórico."));
  const kpis = [
    ["◉", "Recursos evaluados", latest.length, "Total de la célula", "purple"],
    [
      "▥",
      "Promedio general",
      `${avg}/100`,
      latest.length ? "última evaluación por recurso" : "sin evaluaciones",
      "blue",
    ],
    ["◫", "Pendientes por evaluar", pendientes, "Requieren evaluación", "red"],
    ["!", "En observación", observacion, "Requiere seguimiento", "red"],
    ["★", "Top performers", top, "Desempeño sobresaliente", "green"],
  ];
  const recent = evOrdenadas.slice(0, 5);
  target.replaceChildren(
    div(
      "aer-vivid-grid",
      card(
        div(
          "aer-action-hero",
          div(
            "",
            h("h3", "", "Evaluación de recursos"),
            div(
              "sub",
              "Seguimiento del desempeño, histórico de evaluaciones y comentarios.",
            ),
          ),
          button("+ Nueva evaluación", () => actions.open(), "aer-btn primary"),
        ),
        styled(
          div(
            "aer-eval-kpis",
            ...kpis.map((x) =>
              div(
                "aer-vivid-card soft",
                div(
                  "aer-vivid-kpi-head",
                  h("span", `aer-vivid-icon ${x[4]}`, x[0]),
                  div(
                    "",
                    div("aer-vivid-label", x[1]),
                    div("aer-vivid-value", text(x[2])),
                    div("aer-vivid-sub", x[3]),
                  ),
                ),
              ),
            ),
          ),
          { marginTop: "12px" },
        ),
      ),
      div(
        "aer-eval-layout",
        card(
          div("aer-section-title", h("h3", "", "Resumen por recurso"), select),
          div(
            "aer-eval-person-head",
            div(
              "aer-eval-person",
              h("span", "aer-eval-avatar", initials(sel.recurso || "?")),
              div(
                "aer-eval-name",
                h("b", "", sel.recurso || "Sin recurso"),
                h(
                  "small",
                  "",
                  (dashboard.detalleRecursos || []).find(
                    (x) => x.recurso === sel.recurso,
                  )?.rol || "Recurso del proyecto",
                ),
              ),
            ),
            div(
              "aer-eval-score",
              h("b", "", `${Number(sel.score || 0)}/100`),
              h("span", "", category(sel.score)),
            ),
          ),
          div(
            "aer-eval-dims",
            ...[
              ["Calidad", sel.calidad],
              ["Cumplimiento", sel.cumplimiento],
              ["Comunicación", sel.comunicacion],
              ["Colaboración", sel.colaboracion],
              ["Autonomía", sel.autonomia],
            ].map((x) =>
              div(
                "aer-eval-dim",
                h("span", "", x[0]),
                div(
                  "bar",
                  styled(h("i", ""), { width: `${Number(x[1] || 0)}%` }),
                ),
                h("b", "", `${Number(x[1] || 0)}%`),
              ),
            ),
          ),
          div(
            "aer-eval-strengths",
            styled(h("b", "", "Fortalezas identificadas"), {
              fontSize: "10px",
            }),
            div(
              "tags",
              ...(strengths.length
                ? strengths.map((x) => h("span", "", `${x[0]} ${x[1]}%`))
                : [h("span", "", "Sin datos todavía")]),
            ),
          ),
        ),
        card(
          section(
            "Histórico de evaluaciones",
            "Últimas 5 evaluaciones registradas",
          ),
          chart,
          div(
            "aer-eval-chart-labels",
            ...pts.map((x) => h("span", "", dateText(x.fechaEvaluacion))),
          ),
          div(
            "aer-eval-summary-row",
            ...[
              [
                pts.length > 1
                  ? ptsDelta >= 0
                    ? "Tendencia positiva"
                    : "Revisar tendencia"
                  : "—",
                "Desempeño",
              ],
              [
                pts.length > 1
                  ? `${ptsDelta > 0 ? "+" : ""}${ptsDelta} pts`
                  : "—",
                "Cambio periodo",
              ],
              [
                pts.length
                  ? dateText(pts[pts.length - 1].fechaEvaluacion)
                  : "—",
                "Última evaluación",
              ],
            ].map((x) => div("box", h("b", "", x[0]), h("span", "", x[1]))),
          ),
          div(
            "aer-eval-last5",
            ...(recent.length
              ? recent.map((x) =>
                  div(
                    "item",
                    h("span", "", dateText(x.fechaEvaluacion)),
                    h("b", "", x.recurso),
                    h("span", "score", `${x.score}/100`),
                  ),
                )
              : [empty("Sin evaluaciones registradas.")]),
          ),
        ),
        card(
          div(
            "aer-section-title",
            div("", h("h3", "", "Distribución de desempeño")),
          ),
          div(
            "aer-vivid-donut-wrap",
            styled(
              div(
                "aer-donut",
                div(
                  "",
                  h("b", "", text(latest.length)),
                  h("small", "", "recursos"),
                ),
              ),
              {
                background: `conic-gradient(#39bf79 0 ${a1}%,#7350e9 ${a1}% ${a2}%,#f4bd3e ${a2}% ${a3}%,#e64a5d ${a3}% 100%)`,
              },
            ),
            div(
              "aer-vivid-legend",
              ...Object.entries(cats).map(([n, v], i) =>
                div(
                  "row",
                  h(
                    "span",
                    "",
                    styled(h("i", "sw"), {
                      background: ["#39bf79", "#7350e9", "#f4bd3e", "#e64a5d"][
                        i
                      ],
                    }),
                    n,
                  ),
                  h("b", "", text(v)),
                  h("i", ""),
                ),
              ),
            ),
          ),
          ...(prox
            ? [
                div(
                  "aer-vivid-note",
                  h("b", "", "Próxima evaluación"),
                  h("br", ""),
                  styled(h("span", "", dateText(prox.proximaEvaluacion)), {
                    fontSize: "14px",
                    fontWeight: 900,
                  }),
                  h("br", ""),
                  `${text(prox.recurso)} · Responsable: ${prox.evaluador || "—"}`,
                ),
              ]
            : []),
        ),
      ),
      div(
        "aer-eval-bottom",
        card(
          section("Comentarios recientes"),
          div(
            "aer-eval-comments",
            ...(recent.length
              ? recent.map((x) =>
                  div(
                    "aer-eval-comment",
                    h("span", "", dateText(x.fechaEvaluacion)),
                    h("b", "", x.recurso),
                    h("span", "", `“${x.comentario || "Sin comentario"}”`),
                    h("span", "tag", category(x.score)),
                  ),
                )
              : [empty("Sin comentarios.")]),
          ),
        ),
        card(
          section("Últimas evaluaciones"),
          table(
            "aer-eval-history",
            ["Fecha", "Recurso", "Evaluador", "Resultado", "Estado", ""],
            recent.map((x) =>
              h(
                "tr",
                "",
                cell(dateText(x.fechaEvaluacion)),
                cell(text(x.recurso)),
                cell(text(x.evaluador)),
                scoreCell(x.score),
                cell(pill(x)),
                cell(button("⋯", () => actions.open(x.uid))),
              ),
            ),
            "Sin evaluaciones.",
          ),
        ),
      ),
      card(
        section(
          "Historial detallado",
          "Evaluaciones persistidas en AER_Evaluaciones.",
        ),
        styled(
          div(
            "",
            table(
              "aer-eval-history",
              [
                "Fecha",
                "Recurso",
                "Periodo",
                "Evaluador",
                "Score",
                "Categoría",
                "Comentario",
                "Plan de acción",
                "Editar",
              ],
              evOrdenadas.map((x) =>
                h(
                  "tr",
                  "",
                  cell(dateText(x.fechaEvaluacion)),
                  cell(text(x.recurso)),
                  cell(text(x.periodo)),
                  cell(text(x.evaluador)),
                  scoreCell(x.score),
                  cell(pill(x)),
                  cell(x.comentario || "—"),
                  cell(x.planAccion || "—"),
                  cell(button("✎", () => actions.open(x.uid))),
                ),
              ),
              "Sin historial.",
            ),
          ),
          { overflow: "auto" },
        ),
      ),
    ),
  );
}

export function openEvaluation(dashboard, uid, actions, now = new Date()) {
  const x =
    (dashboard.evaluaciones?.filas || []).find((v) => v.uid === uid) || {};
  document.getElementById("aer-modal-back")?.remove();
  const back = el("div", { id: "aer-modal-back", class: "aer-modal-back" }),
    close = () => back.remove();
  back.addEventListener("click", (event) => {
    if (event.target === back) close();
  });
  const field = (label, node, cls = "") => h("label", cls, label, node);
  const select = el(
    "select",
    { id: "ae-rec" },
    ...resources(dashboard).map((n) =>
      el("option", { value: n, selected: x.recurso === n }, n),
    ),
  );
  back.append(
    div(
      "aer-modal",
      styled(
        div(
          "",
          h("h3", "", `${uid ? "Editar" : "Nueva"} evaluación`),
          button("✕", close),
        ),
        { display: "flex", justifyContent: "space-between" },
      ),
      div(
        "aer-formgrid",
        field("Recurso", select),
        field("Evaluador", input(x.evaluador || "", { id: "ae-eval" })),
        field(
          "Fecha evaluación",
          input(x.fechaEvaluacion || now.toISOString().slice(0, 10), {
            id: "ae-fecha",
            type: "date",
          }),
        ),
        field(
          "Próxima evaluación",
          input(x.proximaEvaluacion || "", { id: "ae-prox", type: "date" }),
        ),
        ...[
          ["Calidad", "cal", "calidad"],
          ["Cumplimiento", "cum", "cumplimiento"],
          ["Comunicación", "comu", "comunicacion"],
          ["Colaboración", "col", "colaboracion"],
          ["Autonomía", "aut", "autonomia"],
        ].map(([label, id, key]) =>
          field(
            label,
            input(Number(x[key] || 0), {
              id: `ae-${id}`,
              type: "number",
              min: 0,
              max: 100,
            }),
          ),
        ),
        field(
          "Comentario",
          el("textarea", { id: "ae-com" }, text(x.comentario || "")),
          "aer-span2",
        ),
        field(
          "Plan de acción",
          el("textarea", { id: "ae-plan" }, text(x.planAccion || "")),
          "aer-span2",
        ),
      ),
      styled(
        div(
          "aer-actions",
          ...(uid
            ? [button("Eliminar", () => actions.remove(uid), "aer-btn danger")]
            : []),
          button(
            "Guardar evaluación",
            () => actions.save(uid),
            "aer-btn primary",
          ),
        ),
        { marginTop: "12px" },
      ),
    ),
  );
  document.body.append(back);
  return back;
}
