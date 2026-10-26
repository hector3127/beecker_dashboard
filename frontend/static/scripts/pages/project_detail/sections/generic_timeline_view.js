import { el } from "#app/lib/dom.js";

const node = (cls, ...children) =>
  el("div", { class: "gt-" + cls }, ...children);
const colors = {
  plan: "#C9C9CD",
  real: "#4A2A94",
  suspendido: "#F2A900",
  completado: "#2E7D32",
};
const dayMonth = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "?"
    : String(date.getDate()).padStart(2, "0") +
        "/" +
        String(date.getMonth() + 1).padStart(2, "0");
};

// The generic timeline uses its original model and presentation, with no HTML
// interpolation. Only numeric geometry and the original state color use CSSOM.
export function genericTimelineView(model, now = Date.now()) {
  if (!model)
    return node(
      "empty",
      'Agrega la hoja Historico_Proyectos con las fases planeadas (ej. "Discovery EST") para ver esta sección.',
    );
  const { filasPlan, filasReal, marcadoresAdicionales, meses, minT, rango } =
    model;
  const years = node("years");
  for (let i = 0; i < meses.length; ) {
    const year = meses[i].getFullYear();
    let span = 0;
    while (i + span < meses.length && meses[i + span].getFullYear() === year)
      span++;
    years.append(
      el(
        "div",
        { class: "gt-year", style: { flex: String(span) } },
        String(year),
      ),
    );
    i += span;
  }
  const monthHeader = node(
    "months",
    ...meses.map((month) =>
      node("month", month.toLocaleDateString("es-MX", { month: "short" })),
    ),
  );
  const grid = node(
    "grid",
    node("grid-lines", ...meses.map(() => node("grid-line"))),
  );
  const positionNow = ((now - minT) / rango) * 100;
  if (positionNow >= 0 && positionNow <= 100)
    grid.append(
      el(
        "div",
        { class: "gt-today", style: { left: positionNow + "%" } },
        node("today-label", "HOY"),
      ),
    );

  const row = (item) => {
    const start = new Date(item.inicio).getTime();
    const end =
      item.tipo === "real" && item.enCurso ? now : new Date(item.fin).getTime();
    const left = ((start - minT) / rango) * 100;
    const width = Math.max(0.5, ((end - start) / rango) * 100);
    const days = Math.round((end - start) / 86400000);
    const bar = el("div", {
      class:
        "gt-bar gt-bar-" +
        item.tipo +
        (item.tipo === "real" && item.enCurso ? " gt-active" : ""),
      style: {
        left: left + "%",
        ...(item.tipo === "completado" ? {} : { width: width + "%" }),
      },
    });
    const dateText =
      item.tipo === "completado"
        ? dayMonth(item.inicio)
        : `${dayMonth(item.inicio)} – ${dayMonth(item.fin)}${days > 0 ? " · " + days + " día" + (days === 1 ? "" : "s") : ""}`;
    const label = node("name", item.etiqueta);
    if (item.tipo === "real") {
      const state = model.estadoEtapaReal(item);
      label.append(
        el(
          "span",
          { class: "gt-state", style: { background: state.color } },
          state.texto,
        ),
      );
    }
    const track = node(
      "track",
      bar,
      ...(item.marcadores || []).map((marker) =>
        el(
          "div",
          {
            class: "gt-marker",
            title: marker.tipo,
            style: { left: ((marker.tiempo - minT) / rango) * 100 + "%" },
          },
          marker.icono || "📌",
        ),
      ),
    );
    return node(
      "row",
      node(
        "label",
        label,
        el(
          "div",
          { class: "gt-date", style: { color: colors[item.tipo] } },
          dateText,
        ),
      ),
      track,
    );
  };
  const rows = node("rows");
  for (const [title, items] of [
    ["PLAN ESTIMADO (LÍNEA BASE)", filasPlan],
    ["EJECUCIÓN REAL", filasReal],
  ]) {
    if (items.length) rows.append(node("section", title), ...items.map(row));
  }
  const legend = node(
    "legend",
    ...[
      ["plan", "Planeación"],
      ["real", "Ejecución"],
      ["suspendido", "Suspendido"],
      ["completado", "Completado"],
    ].map(([type, title]) =>
      el("span", {}, el("span", { class: "gt-key gt-key-" + type }), title),
    ),
  );
  const categories = {};
  marcadoresAdicionales.forEach((marker) => {
    if (!categories[marker.etiquetaCategoria])
      categories[marker.etiquetaCategoria] = marker.icono;
  });
  for (const category of Object.keys(categories))
    legend.append(el("span", {}, categories[category] + " " + category));
  return node(
    "scroll",
    node("canvas", years, monthHeader, node("body", grid, rows), legend),
  );
}
