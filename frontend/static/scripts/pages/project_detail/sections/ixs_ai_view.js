import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";

const n = (tag, cls, ...children) =>
  el(
    tag,
    cls ? { class: cls } : {},
    ...children.flat().filter((x) => x != null),
  );
const div = (cls, ...children) => n("div", cls, ...children);
const text = (value) => (value == null ? "" : String(value));
const note = (value) => n("p", "ixai-muted", text(value));
const button = (label, action, primary = false, attrs = {}) =>
  el(
    "button",
    {
      class: "ixai-btn" + (primary ? " primary" : ""),
      onclick: action,
      ...attrs,
    },
    label,
  );
const card = (name, title, ...body) =>
  n("section", "ixai-card", n("h3", "", icon(name), " " + title), ...body);
const pill = (value) => n("span", "ixai-pill", text(value));
const dateOf = (x) =>
  String(
    x.fechaLimiteDev || x.fechaLimite || x.fechaCompromiso || x.fecha || "",
  ).slice(0, 10);
const styled = (node, style) => {
  Object.assign(node.style, style);
  return node;
};
const bar = (width, color) =>
  div(
    "ixai-bar",
    styled(n("i", ""), {
      width: width + "%",
      ...(color ? { background: color } : {}),
    }),
  );

function metric(name, value, label, caption, color, width) {
  return div(
    "ixai-card",
    div(
      "ixai-stat",
      styled(n("span", "ixai-icon", icon(name)), { color }),
      n(
        "span",
        "",
        n("b", "", text(value)),
        styled(n("strong", "", label), { fontSize: "11px" }),
        n("br", ""),
        n("small", "", caption),
      ),
    ),
    bar(width ?? Math.min(100, Math.max(0, Number(value) || 0)), color),
  );
}

function folders(state, type, a) {
  const values =
    (state.driveConfig &&
      (type === "documentos"
        ? state.driveConfig.carpetas
        : state.driveConfig.transcripciones)) ||
    [];
  return values.length
    ? styled(
        div(
          "ixai-muted",
          ...values.map((id, i) =>
            styled(
              div(
                "",
                el(
                  "a",
                  {
                    href: "https://drive.google.com/drive/folders/" + id,
                    target: "_blank",
                    rel: "noopener noreferrer",
                  },
                  `Carpeta ${i + 1} ↗`,
                ),
                button("Quitar", () => a.removeFolder(id, type), false, {
                  type: "button",
                }),
              ),
              {
                display: "flex",
                gap: "7px",
                alignItems: "center",
                overflowWrap: "anywhere",
              },
            ),
          ),
        ),
        { margin: "9px 0" },
      )
    : note(
        `Sin carpetas de ${type === "transcripciones" ? "transcripciones" : "documentos"} vinculadas.`,
      );
}

export function renderDocuments(out, state, query, a) {
  const docs =
    (state.cliente &&
      state.cliente.cliente &&
      state.cliente.cliente.documentos) ||
    [];
  const norm = String(query || "").toLocaleLowerCase("es");
  const local = docs.filter((d) =>
    [d.nombre, d.tipo, d.notas]
      .join(" ")
      .toLocaleLowerCase("es")
      .includes(norm),
  );
  const drive = (state.driveFiles || []).filter(
    (d) =>
      d.tipo === "documentos" &&
      d.nombre.toLocaleLowerCase("es").includes(norm),
  );
  const link = (url) =>
    el(
      "a",
      { href: url, target: "_blank", rel: "noopener noreferrer" },
      "Abrir ↗",
    );
  const rows = drive.map((d) =>
    div(
      "ixai-doc-row",
      n(
        "span",
        "",
        text(d.nombre) + " ",
        n(
          "small",
          "",
          `${text(d.fecha)} · Drive${d.minuta ? " · Minuta" : ""}`,
        ),
      ),
      n(
        "span",
        "",
        link(d.url),
        ...(d.legible ? [" ", button("Leer", () => a.document(d.id))] : []),
      ),
    ),
  );
  rows.push(
    ...local.map((d) =>
      div(
        "ixai-doc-row",
        n(
          "span",
          "",
          text(d.nombre || "Documento") + " ",
          n("small", "", text(d.tipo || "Cliente")),
        ),
        /^https:\/\//i.test(String(d.url || ""))
          ? link(String(d.url))
          : "Sin vínculo",
      ),
    ),
  );
  out.replaceChildren(
    ...(rows.length
      ? rows
      : [
          note(
            state.driveLoading
              ? "Buscando archivos…"
              : state.driveConfig && state.driveConfig.folderId
                ? "No hay documentos que coincidan."
                : "Conecta la carpeta de Drive de este proyecto para ver sus documentos y minutas.",
          ),
        ]),
  );
}

export function renderTranscripts(out, state, a) {
  const files = (state.driveFiles || []).filter(
      (f) => f.tipo === "transcripciones",
    ),
    chosen = state.driveSelected || [];
  out.replaceChildren(
    ...(files.length
      ? [
          styled(
            div(
              "",
              ...files.map((f) => {
                const input = el("input", {
                  type: "checkbox",
                  disabled: !f.legible,
                  ...(!f.legible
                    ? {
                        title:
                          "Solo se puede extraer texto de Google Docs y TXT",
                      }
                    : {}),
                  onchange: () => a.toggleTranscript(f.id, input),
                });
                input.checked = chosen.includes(f.id);
                return styled(
                  n(
                    "label",
                    "",
                    input,
                    styled(
                      n(
                        "span",
                        "",
                        n("b", "", text(f.nombre)),
                        styled(
                          n(
                            "small",
                            "",
                            `${text(f.fecha)} · ${f.legible ? "Disponible para generar minuta" : "Solo vínculo"}`,
                          ),
                          { display: "block", color: "#757998" },
                        ),
                      ),
                      { flex: "1", minWidth: "0", overflowWrap: "anywhere" },
                    ),
                    el(
                      "a",
                      {
                        href: f.url,
                        target: "_blank",
                        rel: "noopener noreferrer",
                      },
                      "Abrir ↗",
                    ),
                  ),
                  {
                    display: "flex",
                    alignItems: "center",
                    gap: "9px",
                    padding: "9px",
                    borderBottom: "1px solid #eeeafa",
                  },
                );
              }),
            ),
            {
              maxHeight: "330px",
              overflow: "auto",
              border: "1px solid #e1e3fa",
              borderRadius: "10px",
            },
          ),
          note(chosen.length + " seleccionado(s)"),
        ]
      : [
          note(
            "Agrega una carpeta de transcripciones y pulsa Actualizar para mostrar los archivos.",
          ),
        ]),
  );
}

export function renderAi(root, state, deps) {
  const s = state,
    d = deps.project || {},
    ctx = deps.context,
    changed = deps.changed,
    a = deps.actions;
  const wi = (s.azure && s.azure.allItems) || [],
    open = wi.filter(
      (w) =>
        !/closed|done|resolved|complet|cerrad/i.test(
          String(w.state || w.estado || ""),
        ),
    ).length;
  const today = new Date().toISOString().slice(0, 10),
    commitments = (s.plan && s.plan.compromisos) || [],
    vacations = (s.plan && s.plan.vacaciones) || [];
  const late = commitments.filter((x) => {
    const date = dateOf(x);
    return (
      date &&
      date < today &&
      !/complet|cerrad|resuelt/i.test(String(x.estado || ""))
    );
  }).length;
  const soon = vacations.filter((x) => {
    const date = String(x.inicio || x.fechaInicio || "").slice(0, 10);
    return (
      date >= today &&
      date <= new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10)
    );
  }).length;
  const result = (s.analisis && s.analisis.analisis) || {},
    findings = Array.isArray(result.hallazgos) ? result.hallazgos : [],
    recs = Array.isArray(result.recomendaciones) ? result.recomendaciones : [],
    alerts = Array.isArray(result.alertas) ? result.alertas : [];
  const head = div(
    "ixai-head",
    div(
      "ixai-title",
      n("span", "ixai-icon", icon("sparkles")),
      div(
        "",
        n("h2", "", "Centro de Inteligencia del Proyecto"),
        n(
          "p",
          "",
          "Análisis a partir de Azure DevOps, Clockify, planeación, recursos y seguimiento.",
        ),
      ),
    ),
    div(
      "ixai-head-actions",
      button("Actualizar memoria", a.memory),
      button([icon("layers"), " Generar reporte"], () => a.report()),
      button(
        s.loading ? "Analizando…" : "＋ Actualizar análisis",
        a.analyze,
        true,
        { id: "ixai-analyze", disabled: s.loading },
      ),
    ),
  );
  // el.append accepts nodes; button labels containing SVG are appended separately.
  const report = head.querySelectorAll(".ixai-head-actions button")[1];
  report.replaceChildren(icon("layers"), " Generar reporte");
  const available = ctx.fuentesDisponibles,
    memory = s.memoria && s.memoria.actual;
  const meta = div(
    "ixai-meta",
    n(
      "span",
      "",
      icon("clock"),
      " Último análisis: " +
        text((s.analisis && s.analisis.fecha) || "Pendiente"),
    ),
    n(
      "span",
      "",
      icon("layers"),
      " Memoria: " + text((memory && memory.fecha) || "Sin corte"),
    ),
    n("span", "", icon("folder"), " Fuentes: " + available.join(", ")),
    n(
      "span",
      "ixai-sync",
      "● " +
        (available.length === 7
          ? "Sincronizado correctamente"
          : available.length + "/7 fuentes conectadas"),
    ),
  );
  const metrics = styled(
    div(
      "ixai-grid6",
      metric(
        "layers",
        findings.length,
        "Hallazgos detectados",
        s.analisis ? "Análisis actual" : "Pendiente de analizar",
        "#6832e0",
      ),
      metric(
        "target",
        recs.length,
        "Acciones sugeridas",
        "Revisar recomendaciones",
        "#378af1",
      ),
      metric(
        "warning",
        alerts.length,
        "Alertas activas",
        "Análisis IA",
        "#e63d67",
      ),
      metric(
        "clock",
        changed && !changed.incompleto ? String(changed.nuevos) : "—",
        "Cambios desde el corte",
        changed && !changed.incompleto
          ? "WIs nuevos"
          : "Sin cortes comparables",
        "#e49a20",
        Math.min(100, Math.max(0, Number(late) || 0)),
      ),
      metric(
        "folder",
        available.length + "/7",
        "Fuentes disponibles",
        "Conectadas",
        "#16a56e",
        (available.length / 7) * 100,
      ),
      metric(
        "chart",
        [...findings, ...alerts, ...recs, ...(result.resumen || [])].filter(
          (x) => x && x.evidencias && x.evidencias.length,
        ).length,
        "Afirmaciones verificadas",
        "Con evidencias",
        "#6333e5",
      ),
    ),
    { marginTop: "14px" },
  );
  const summary = div(
    "ixai-summary",
    ...(result.resumen && result.resumen.length
      ? result.resumen.map((x, i) =>
          n(
            "p",
            "",
            n("span", "ixai-n", String(i + 1)),
            " " + text(x.texto || x),
          ),
        )
      : [
          n(
            "p",
            "",
            "Pulsa «Actualizar análisis» para generar un resumen de las fuentes disponibles. La IA no se ejecuta automáticamente.",
          ),
        ]),
  );
  const sumMetrics = div(
    "ixai-sum-metrics",
    ...[
      ["Tiempo", d.avance && d.avance.pct],
      ["Esfuerzo", d.totalesRecursos && d.totalesRecursos.pctCumplimientoHoras],
      ["Costo", d.kpisExtra && d.kpisExtra.pctCumplimientoFinanciero],
    ]
      .filter(
        (x) => x[1] != null && x[1] !== "" && Number.isFinite(Number(x[1])),
      )
      .map(([name, value]) =>
        n(
          "span",
          "",
          `${name} · ${Number(value).toFixed(1)}%`,
          n(
            "span",
            "ixai-bar",
            styled(n("i", ""), {
              width: Math.min(100, Math.max(0, Number(value))) + "%",
            }),
          ),
        ),
      ),
    ...(d.proyecto && d.proyecto.nivelRiesgoFecha
      ? [n("span", "", "Riesgo · " + text(d.proyecto.nivelRiesgoFecha))]
      : []),
  );
  const summaryCard = card(
    "layers",
    "Resumen inteligente",
    div("ixai-sum-grid", summary, sumMetrics),
    button("Ver evidencias", () => a.evidence("resumen", 0)),
    " ",
    button("Preparar resumen ejecutivo", () => a.report(), true),
    div(
      "ixai-pills",
      pill(result.estado || "Pendiente de análisis"),
      ...(s.analisis && s.analisis.fecha ? [pill(s.analisis.fecha)] : []),
    ),
  );
  const rows = (list, kind) =>
    list.map((x, i) =>
      el(
        "div",
        {
          class: "ixai-line",
          title: "Ver evidencias",
          onclick: () => a.evidence(kind, i),
        },
        n("strong", "", text(x.titulo || "")),
        n("span", "", text(x.detalle || "")),
        div(
          "ixai-pills",
          pill(x.fuente || "Proyecto"),
          ...(x.prioridad ? [pill(x.prioridad)] : []),
        ),
      ),
    );
  const attention = card(
    "warning",
    "Atención inteligente",
    ...(alerts.length
      ? rows(alerts, "alertas")
      : [
          note("Sin alertas generadas. Actualiza el análisis para revisarlas."),
        ]),
    ...rows(findings.slice(0, 3), "hallazgos"),
    button("Ver todos los hallazgos", () => a.evidence("alertas", 0)),
  );
  const recommendations = card(
    "target",
    "Recomendaciones IA",
    div(
      "ixai-recs",
      ...(recs.length
        ? recs.slice(0, 4).map((r, i) =>
            div(
              "ixai-rec",
              n(
                "span",
                "ixai-icon",
                icon(["chart", "layers", "people", "target"][i % 4]),
              ),
              n("strong", "", text(r.titulo || "Recomendación")),
              div("", text(r.detalle || "")),
              pill(r.fuente || "Proyecto"),
              styled(
                div(
                  "",
                  button("Ver evidencia", () => a.evidence("recomendacion", i)),
                  button("Crear acción", () => a.action(i), true),
                  button("Riesgo", () => a.raid("Risk", i)),
                  button("Issue", () => a.raid("Issue", i)),
                  button("Oportunidad", () => a.raid("Opportunity", i)),
                ),
                {
                  display: "flex",
                  gap: "5px",
                  flexWrap: "wrap",
                  marginTop: "9px",
                },
              ),
            ),
          )
        : [
            n(
              "span",
              "ixai-muted",
              "Las recomendaciones aparecerán después del análisis.",
            ),
          ]),
    ),
  );
  const sources = div(
    "ixai-sources",
    ...[
      [
        "calendar",
        "Planeación",
        s.plan
          ? commitments.length +
            " compromisos · " +
            vacations.length +
            " vacaciones"
          : null,
        "plan",
        "planeacion",
      ],
      [
        "chart",
        "Esfuerzo",
        s.clockify ? ctx.registrosClockifyTotal + " registros Clockify" : null,
        "clockify",
        "esfuerzo",
      ],
      [
        "people",
        "Recursos",
        s.resources ? (s.resources.filas || []).length + " asignaciones" : null,
        "resources",
        "recursos",
      ],
      [
        "layers",
        "Azure DevOps",
        s.azure ? wi.length + " Work Items · " + open + " abiertos" : null,
        "azure",
        "azure",
      ],
      [
        "warning",
        "RAID",
        s.raid ? (s.raid.registros || []).length + " registros" : null,
        "raid",
        "riesgos",
      ],
    ].map(([name, title, value, key, tab]) =>
      el(
        "div",
        {
          class: "ixai-source",
          tabindex: 0,
          role: "button",
          onclick: () => a.tab(tab),
          onkeydown: (e) => {
            if (e.key === "Enter") a.tab(tab);
          },
        },
        n("span", "ixai-icon", icon(name)),
        n("strong", "", title),
        n("p", "", text(value || s.sourceErrors[key] || "Cargando fuente…")),
        n("span", "ixai-more", "Profundizar →"),
      ),
    ),
  );
  const input = el("input", {
    id: "ixai-question",
    placeholder: "Escribe una pregunta sobre el proyecto…",
    required: true,
    minlength: 5,
    oninput: () => {
      s.question = input.value;
    },
  });
  input.value = s.question;
  const ask = card(
    "sparkles",
    "Pregunta a la IA",
    el(
      "form",
      { class: "ixai-ask", onsubmit: a.ask },
      input,
      button("Preguntar", null, true, { id: "ixai-ask", type: "submit" }),
    ),
    div(
      "ixai-pills",
      ...[
        "¿Qué debo atender esta semana?",
        "¿Qué recursos están excedidos?",
        "¿Cómo vamos en el proyecto?",
      ].map((q) => button(q, () => a.setQuestion(q))),
    ),
    ...(s.respuesta ? [div("ixai-answer", text(s.respuesta))] : []),
  );
  const assistant = card(
    "sparkles",
    "Asistente de seguimiento",
    div(
      "ixai-actions",
      button("Resumen semanal", () => a.report("Delivery Manager")),
      button("Preparar minuta", a.createMinute),
      button("Reporte ejecutivo", () => a.report()),
      button("Redactar comunicado", a.communique),
    ),
    styled(
      div(
        "ixai-muted",
        `${available.join(" · ")} · ${soon} vacaciones próximas · ${late} compromisos vencidos`,
      ),
      { marginTop: "10px" },
    ),
  );
  const mins = s.minutas || [],
    last = mins[0];
  const latest = card(
    "layers",
    "Última minuta",
    ...(last
      ? [
          n("strong", "", text(last.tema)),
          note(last.fecha),
          note(
            last.contenido.slice(0, 220) +
              (last.contenido.length > 220 ? "…" : ""),
          ),
          button("Ver minuta", () => a.minute(0)),
        ]
      : [note("No hay minutas guardadas para este proyecto.")]),
    button("Preparar nueva minuta", a.createMinute, true),
  );
  const driveMinutes = (s.driveFiles || []).filter((f) => f.minuta);
  const historyRows = mins.slice(0, 12).map((m, i) =>
    n(
      "tr",
      "",
      n(
        "td",
        "",
        el("input", {
          type: "checkbox",
          class: "ixai-minute-select",
          value: i,
        }),
      ),
      n("td", "", text(m.fecha)),
      n("td", "", text(m.tema)),
      n("td", "", m.contenido.slice(0, 110)),
      n(
        "td",
        "",
        button("Ver minuta", () => a.minute(i)),
      ),
    ),
  );
  historyRows.push(
    ...driveMinutes.slice(0, 12).map((f) =>
      n(
        "tr",
        "",
        n("td", "", "Drive"),
        n("td", "", text(f.fecha)),
        n("td", "", text(f.nombre)),
        n("td", "", "Documento de la carpeta conectada"),
        n(
          "td",
          "",
          button("Ver documento", () => a.document(f.id)),
        ),
      ),
    ),
  );
  if (!mins.length && !driveMinutes.length)
    historyRows.push(
      n(
        "tr",
        "",
        el(
          "td",
          { colspan: 5 },
          "Conecta una carpeta de Drive con minutas o guarda una minuta nueva.",
        ),
      ),
    );
  const history = card(
    "layers",
    "Historial de minutas y acuerdos",
    button("Resumir selección con IA", a.summarize),
    n(
      "table",
      "ixai-table",
      n(
        "thead",
        "",
        n(
          "tr",
          "",
          ...["Elegir", "Fecha", "Reunión", "Contenido", "Acción"].map((t) =>
            n("th", "", t),
          ),
        ),
      ),
      n("tbody", "", ...historyRows),
    ),
  );
  const docResults = el("div", { id: "ixai-doc-results" }),
    transcriptResults = el("div", { id: "ixai-transcript-results" });
  const filter = el("input", {
    id: "ixai-doc-filter",
    placeholder: "Buscar documentos o minutas…",
    oninput: () => renderDocuments(docResults, s, filter.value, a),
  });
  const docs =
    (s.cliente && s.cliente.cliente && s.cliente.cliente.documentos) || [];
  const documents = el(
    "details",
    { class: "ixai-card", open: true },
    styled(
      n(
        "summary",
        "",
        icon("folder"),
        ` Documentos y conocimiento del proyecto (${docs.length + (s.driveFiles || []).length})`,
      ),
      { cursor: "pointer", fontWeight: "800" },
    ),
    note(
      `Carpeta exclusiva de ${text(s.id)}. Se muestra el contenido de Google Docs y TXT al abrirlos; otros archivos se abren en Drive.`,
    ),
    div(
      "ixai-doc-search",
      filter,
      button("＋ Agregar carpeta", () => a.configureDrive("documentos")),
      button(s.driveLoading ? "Buscando…" : "Actualizar", a.loadDrive, false, {
        disabled: s.driveLoading,
      }),
    ),
    folders(s, "documentos", a),
    ...(s.driveError
      ? [styled(n("p", "", text(s.driveError)), { color: "#c32a53" })]
      : []),
    docResults,
  );
  const transcripts = n(
    "section",
    "ixai-card",
    div(
      "ixai-card-head",
      n("h3", "", icon("layers"), " Transcripciones para minutas"),
      button("＋ Agregar carpeta de transcripciones", () =>
        a.configureDrive("transcripciones"),
      ),
    ),
    note(
      "Selecciona hasta cinco transcripciones. El texto se envía a Claude solo al generar el borrador.",
    ),
    folders(s, "transcripciones", a),
    transcriptResults,
    styled(
      div(
        "",
        button("✦ Generar borrador", a.prepareDriveMinute, true),
        button("Escribir minuta manualmente", a.createMinute),
      ),
      { display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "10px" },
    ),
  );
  root.replaceChildren(
    div(
      "ixai",
      n("section", "ixai-card", head, meta, metrics),
      ...(s.error
        ? [styled(div("ixai-card", text(s.error)), { color: "#c32a53" })]
        : []),
      div("ixai-main", summaryCard, attention),
      recommendations,
      sources,
      deps.panels(deps.capacity, changed, () => a.tab("recursos")),
      div("ixai-bottom ixai-three", ask, assistant, latest),
      div("ixai-last", history, documents),
      transcripts,
    ),
  );
  renderDocuments(docResults, s, "", a);
  renderTranscripts(transcriptResults, s, a);
}
