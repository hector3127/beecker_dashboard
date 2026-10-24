import {
  presentation,
  memoryDate,
  minuteSummary,
} from "./aer_ai_presentation_model.js";
import {
  el,
  h,
  div,
  styled,
  button,
  text,
  muted,
  card,
  title,
  chip,
  formatted,
  chat,
} from "./aer_ai_dom.js";
import { minutesTable, documents } from "./aer_ai_documents_view.js";

function kpi(icon, label, value, note, tone) {
  return card(
    div(
      "aeri-stat",
      h("span", `aeri-icon ${tone}`, icon),
      styled(
        div(
          "",
          h("label", "", label),
          h("strong", "", text(value)),
          h("small", "", note),
        ),
        { minWidth: 0 },
      ),
    ),
  );
}
function metric(name, num, color, right) {
  const n = Math.max(0, Number(num) || 0);
  return div(
    "aeri-metric",
    styled(el("span", { title: text(name) }, text(name)), {
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap",
    }),
    h(
      "span",
      "aeri-track",
      styled(h("i", "aeri-fill"), {
        display: "block",
        width: `${Math.min(100, n)}%`,
        background: color,
      }),
    ),
    styled(h("b", "", text(right == null ? Math.round(n) + "%" : right)), {
      textAlign: "right",
      fontSize: "10px",
    }),
  );
}
const mini = (name, detail, extra) =>
  div(
    "aeri-mini",
    div("", h("b", "", name), h("br", ""), h("small", "", detail || "")),
    chip(extra || ""),
  );
export function renderAi(target, dashboard, s, a) {
  const { f, anal, mins, k, memoria, tz, resumen, recs, dim } = presentation(
    dashboard,
    s,
  );
  const memory = [];
  if (anal)
    memory.push(
      el(
        "div",
        { class: "aeri-memory", role: "status" },
        div(
          "",
          h(
            "strong",
            "",
            "◷ " +
              (memoria
                ? "Memoria del " + memoryDate(memoria)
                : "Análisis disponible sin fecha de guardado"),
          ),
          h(
            "small",
            "",
            (memoria
              ? "Hora registrada en " +
                (tz || "la zona horaria de Apps Script") +
                ". "
              : "Este análisis aún no tiene fecha confirmada en Sheets. ") +
              (s.analisis.persistido === false
                ? "No se pudo guardar en Sheets; revisa el error antes de cerrar."
                : "Este es el último análisis almacenado en Sheets; no refleja cambios posteriores hasta actualizarlo."),
          ),
        ),
        button(
          s.cargando ? "Actualizando…" : "↻ Actualizar memoria",
          () => a.analyze(true),
          "aer-btn",
          { disabled: !!s.cargando },
        ),
      ),
    );
  else if (s.cargandoAnalisis)
    memory.push(
      div(
        "aeri-memory pending",
        div(
          "",
          h("strong", "", "◷ Buscando última memoria en Sheets…"),
          h("small", "", "No se está llamando a Claude."),
        ),
      ),
    );
  const response = el("div", { id: "aeri-response" });
  const savedChat = chat(s);
  if (savedChat) response.append(savedChat);
  const evidence = [
    ["📅", "Planeación", "planeacion"],
    ["▥", "Esfuerzo", "esfuerzo"],
    ["⚠", "Riesgos", "riesgos"],
    ["▤", "Acciones", "acciones"],
    ["☀", "Vacaciones", "planeacion"],
    ["♟", "Recursos", "recursos"],
  ];
  const summary = s.resumenEjecutivo || {};
  target.replaceChildren(
    div(
      "aeri",
      div(
        "aeri-head",
        div(
          "aeri-title",
          h("span", "icon", "✦"),
          div(
            "",
            h("h3", "", "Inteligencia del proyecto"),
            muted(
              "Análisis de planeación, Clockify, riesgos, acciones y capacidad • Claude Haiku 4.5",
            ),
          ),
        ),
        div(
          "aer-actions",
          button(
            anal ? "↻ Actualizar análisis" : "✦ Analizar con Claude",
            () => a.analyze(!!anal),
            "aer-btn primary",
            { id: "aeri-analyze" },
          ),
          button("✦ Generar resumen ejecutivo", a.generateSummary, "aer-btn", {
            id: "aeri-generate-summary",
          }),
          button("▤ Generar minuta", a.openMinute),
          button("⚙ Configuración minuta", a.config),
          button("⌕ Buscar minutas", a.files, "aer-btn", {
            id: "aeri-top-scan",
          }),
        ),
      ),
      ...memory,
      div(
        "aeri-kpis",
        kpi(
          "⚠",
          "Alertas detectadas",
          f.alerts.length,
          "indicadores objetivos",
          "red",
        ),
        kpi(
          "💡",
          "Recomendaciones IA",
          recs.length,
          anal ? "generadas por Claude" : "por generar",
          "blue",
        ),
        kpi(
          "◔",
          "Próximos 30 días",
          f.prox.length + " compromisos",
          "vencen en el periodo",
          "gold",
        ),
        kpi(
          "▤",
          "Acciones abiertas",
          f.abiertos.length,
          "desde Acciones",
          "blue",
        ),
        kpi(
          "▣",
          "Minutas IA",
          mins.length,
          mins.length ? "guardadas en este proyecto" : "sin minutas guardadas",
          "green",
        ),
      ),
      div(
        "aeri-row",
        card(
          title(
            "✦ Resumen IA",
            chip(
              anal
                ? s.analisis.restaurado
                  ? "↺ Último análisis guardado"
                  : s.analisis.cache
                    ? "♻ Caché"
                    : "Claude Haiku 4.5"
                : "Indicadores automáticos",
            ),
          ),
          styled(
            div(
              "aeri-row",
              div(
                "",
                ...resumen.map((x) =>
                  div(
                    "aeri-point",
                    h("span", "bullet", "●"),
                    h("p", "", text(x)),
                  ),
                ),
              ),
              div(
                "",
                metric("Tiempo", k.tiempoPct, "#e9a313"),
                metric("Esfuerzo", dim, "#1ba468"),
                metric("Costo", Math.max(0, 100 - k.consumoPct), "#5c30dc"),
                metric(
                  "Riesgo",
                  Number((dashboard.riesgos || {}).score || 0),
                  "#e9a313",
                ),
              ),
            ),
            { gridTemplateColumns: "1fr 1fr", gap: "12px" },
          ),
          div(
            "aeri-evidence",
            ...evidence.map((x) =>
              button(x[0] + " " + x[1], () => a.tab(x[2])),
            ),
          ),
        ),
        card(
          title(
            "💡 Recomendaciones IA",
            h(
              "span",
              "aeri-muted",
              anal
                ? s.analisis.restaurado
                  ? "Recuperadas del análisis guardado"
                  : "Generadas a partir del proyecto"
                : s.cargandoAnalisis
                  ? "Recuperando análisis anterior…"
                  : "Pulsa «Analizar con Claude»",
            ),
          ),
          ...(recs.length
            ? recs.map((r, i) =>
                div(
                  "aeri-rec",
                  h("span", "dot"),
                  div(
                    "",
                    h("b", "", text(r.titulo)),
                    h("small", "", text(r.detalle)),
                  ),
                  styled(
                    button((r.area || "Acciones") + " →", () =>
                      a.recommendation(i),
                    ),
                    { fontSize: "9px", padding: "5px" },
                  ),
                ),
              )
            : [
                muted(
                  s.cargandoAnalisis
                    ? "Buscando un análisis guardado, sin consultar a Claude…"
                    : "La pestaña no genera cargos por abrirse. El análisis se consulta solo cuando presionas el botón.",
                ),
              ]),
        ),
      ),
      div(
        "aeri-grid3",
        card(
          title("▥ Pronóstico y capacidad (30 días)", chip("6 pts = 100%")),
          ...((f.c.c || []).length
            ? (f.c.c || [])
                .slice(0, 6)
                .map((x) =>
                  metric(
                    x.r,
                    Math.round((x.o / 6) * 100),
                    x.o > 6 ? "#e43855" : x.o === 6 ? "#e99b11" : "#6638df",
                    x.o + "/6",
                  ),
                )
            : [muted("Sin esfuerzos asignados en planeación.")]),
          div(
            "aeri-mutedfoot",
            `Vacaciones aprobadas próximas: ${f.vac.length}. El pronóstico es una aproximación sobre el esfuerzo capturado, no una estimación de Claude.`,
          ),
        ),
        card(
          title("✧ Preguntar a la IA", chip("Bajo consumo")),
          div(
            "aeri-form",
            el("input", {
              id: "aeri-question",
              maxlength: 380,
              placeholder: "Pregunta sobre este proyecto...",
              onkeydown: (e) => {
                if (e.key === "Enter") a.ask();
              },
            }),
            button("➤", a.ask, "aer-btn primary", { id: "aeri-ask" }),
          ),
          muted("Sugerencias rápidas:"),
          styled(
            div(
              "aeri-evidence",
              ...[
                "¿Qué compromisos están en riesgo?",
                "¿Quién está sobreasignado?",
                "¿Qué afectan las vacaciones?",
                "Resume el proyecto para comité",
              ].map((q) => button(q, () => a.question(q))),
            ),
            { border: 0, marginTop: "3px", paddingTop: "3px" },
          ),
          response,
        ),
        card(
          h("h3", "", "◎ Decisiones / acciones sugeridas"),
          mini(
            "Crear acción",
            "Abre el formulario existente; requiere Guardar.",
            "Acciones",
          ),
          mini(
            "Actualizar riesgo",
            "Abre el formulario existente; requiere Guardar.",
            "Riesgos",
          ),
          mini("Preparar correo", "Claude redacta un borrador editable.", "IA"),
          div(
            "aeri-evidence",
            button("＋ Acción", a.action),
            button("＋ Riesgo", a.risk),
            button("✉ Correo", a.mail),
          ),
        ),
      ),
      div(
        "aeri-row",
        card(
          title(
            "▤ Resumen automático de minuta",
            button(mins.length ? "Ver minuta →" : "Generar minuta →", () =>
              mins.length ? a.minute(0) : a.openMinute(),
            ),
          ),
          styled(
            muted(
              mins.length
                ? "Última minuta: " +
                    (mins[0].tema || "Sin tema") +
                    " · " +
                    (mins[0].fecha || "—")
                : "Sin minutas guardadas en este proyecto",
            ),
            { marginBottom: "9px" },
          ),
          div(
            "aeri-minuta-short",
            mins.length
              ? minuteSummary(mins[0].contenido || "")
              : "Genera y guarda una minuta para mostrar aquí su resumen.",
          ),
          div(
            "aeri-mutedfoot",
            "Este bloque resume la última minuta guardada en AER_IA_Minutas; no muestra el resumen ejecutivo.",
          ),
        ),
        card(
          title(
            "▤ Resumen ejecutivo automático",
            button("Ver resumen →", a.summary),
          ),
          styled(
            muted(
              summary.guardado
                ? "Última memoria: " + summary.guardado
                : "Se guardará en AER_IA_Resumenes",
            ),
            { marginBottom: "9px" },
          ),
          styled(
            div(
              "aeri-exec-preview",
              formatted(
                (
                  summary.contenido ||
                  "Aún no hay resumen ejecutivo. Pulsa «Generar resumen ejecutivo»."
                ).slice(0, 750),
              ),
            ),
            {
              maxHeight: "158px",
              overflowY: "auto",
              lineHeight: 1.6,
              overflowWrap: "anywhere",
            },
          ),
        ),
      ),
      card(
        title(
          "▤ Historial de minutas y acuerdos",
          button(
            s.historialCompleto ? "Ver menos ↑" : "Ver historial →",
            a.history,
          ),
        ),
        minutesTable(s.historialCompleto ? mins : mins.slice(0, 5), a),
        div(
          "aeri-mutedfoot",
          "Claude Haiku 4.5: consulta bajo demanda; contexto resumido sin correos ni registros individuales de Clockify. Coste estimado visible después de cada consulta.",
        ),
      ),
      documents(s, a),
    ),
  );
}
