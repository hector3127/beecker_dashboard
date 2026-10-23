import { months, cats, colors, num, norm } from "./model.js";
import {
  node,
  text,
  styled,
  button,
  icon,
  heading,
  track,
  monthSelect,
  cell,
  svg,
  input,
  legend,
} from "./ui.js";

export function selectedArea(state, selection, model, actions) {
  const {
    monthly,
    indices,
    period,
    picked,
    m,
    cap,
    annualCap,
    hours,
    fact,
    ratio,
    fmtPct,
  } = model.selectedArea();
  const card = (title, value, symbol, color, note, bar) =>
    node(
      "article",
      "gm-kpi ga-kpi",
      node(
        "div",
        "gm-kpi-label",
        styled(
          "span",
          "gm-icon",
          { color, background: color + "18" },
          icon(symbol),
        ),
        text("span", title),
      ),
      styled("strong", null, { color }, value),
      text("small", note),
      track(Math.min(100, Math.max(0, bar || 0)), color),
    );
  const cards = node(
    "div",
    "ga-kpis",
    card(
      "Horas registradas",
      picked.length ? num(hours) : "NA",
      "clock",
      "#6330d7",
      period,
      100,
    ),
    card(
      selection.areaMonth < 0 ? "Capacidad acumulada" : "Capacidad mensual",
      num(cap),
      "layers",
      "#5274ee",
      period,
      100,
    ),
    card(
      "% Facturable",
      fmtPct(ratio(fact, annualCap)),
      "target",
      "#18af78",
      "Facturables / capacidad del período",
      ratio(fact, annualCap),
    ),
    card(
      "No facturables",
      m ? num(m.categorias["No Facturables"]) : "NA",
      "money",
      "#e54486",
      period,
      ratio(m?.categorias["No Facturables"] || 0, cap),
    ),
    card(
      "Recursos únicos",
      m ? num(m.recursos) : "NA",
      "people",
      "#8a42ef",
      period,
      100,
    ),
    card(
      "Nivel de ocupación",
      fmtPct(ratio(hours, annualCap)),
      "bars",
      "#e6971a",
      "Horas / capacidad del período",
      ratio(hours, annualCap),
    ),
  );
  const series = [
    ["Facturable", "#7d41ef"],
    ["No Facturables", "#c5b0f7"],
    ["Administrativas", "#5486ee"],
    ["Vacaciones", "#41c4a0"],
  ];
  const sums = monthly.map((a) =>
      a ? series.reduce((n, [c]) => n + (a.categorias[c] || 0), 0) : 0,
    ),
    max = Math.max(1, ...sums),
    height = 135;
  const chart = svg("svg", {
    viewBox: "0 0 650 190",
    role: "img",
    "aria-label": "Conceptos de horas por mes",
  });
  for (let t = 0; t <= 4; t++) {
    const y = height - (height * t) / 4 + 10;
    chart.append(
      svg("path", { d: "M40 " + y + "H640", stroke: "#ece9f6" }),
      svg(
        "text",
        {
          x: 33,
          y: y + 4,
          "text-anchor": "end",
          fill: "#9188b0",
          "font-size": 10,
        },
        num((max * t) / 4),
      ),
    );
  }
  monthly.forEach((a, i) => {
    const x = 48 + i * 49;
    let y = height + 10;
    for (const [cat, color] of series) {
      const h = a ? Math.max(0, ((a.categorias[cat] || 0) / max) * height) : 0;
      y -= h;
      chart.append(
        svg(
          "rect",
          { x, y, width: 30, height: h, fill: color },
          svg(
            "title",
            {},
            months[i] +
              " · " +
              cat +
              ": " +
              (a ? num(a.categorias[cat] || 0) : "NA"),
          ),
        ),
      );
    }
    chart.append(
      svg(
        "text",
        {
          x: x + 15,
          y: 166,
          "text-anchor": "middle",
          fill: "#756b97",
          "font-size": 10,
        },
        months[i].slice(0, 3),
      ),
    );
  });
  const perConcept = new Map();
  for (const i of indices)
    for (const d of state.data[model.key(i)]?.detalle || []) {
      if (d.area !== state.area || !(d.horas > 0)) continue;
      const c = d.categoria || "Sin clasificación";
      if (!perConcept.has(c)) perConcept.set(c, new Set());
      perConcept.get(c).add(norm(d.recurso));
    }
  const ranks = Array.from(perConcept, ([name, p]) => ({
    name,
    value: p.size,
  })).sort((a, b) => b.value - a.value);
  const charts = node(
    "div",
    "ga-charts",
    node(
      "section",
      "gm-card",
      heading("Distribución por concepto", "target"),
      text(
        "p",
        "Horas por mes · conceptos mostrados, con posibles solapamientos",
        "ga-sub",
      ),
      chart,
      legend(series),
    ),
    node(
      "section",
      "gm-card",
      node(
        "header",
        "ga-chart-header",
        heading("Recursos por concepto", "people"),
        monthSelect(
          selection.areaMonth,
          (v) => actions.set("areaMonth", Number(v)),
          { "aria-label": "Mes para indicadores del área" },
        ),
      ),
      text("p", "Personas únicas con horas · " + period, "ga-sub"),
      ranks.map((r, i) =>
        node(
          "div",
          "gm-rank",
          text("span", r.name),
          track(
            ranks[0].value ? (100 * r.value) / ranks[0].value : 0,
            colors[i % colors.length],
          ),
          text("b", r.value),
        ),
      ),
      !ranks.length
        ? text(
            "p",
            "Sin detalle disponible para el mes seleccionado.",
            "gse-note",
          )
        : null,
    ),
  );
  const holidays = node(
    "section",
    "gm-card ga-holidays",
    node(
      "h3",
      null,
      icon("calendar"),
      " Días festivos por mes ",
      styled(
        "small",
        null,
        { marginLeft: "auto", color: "#8b81a4", fontWeight: 400 },
        "Editables",
      ),
    ),
    node(
      "div",
      "gse-holidays",
      months.map((name, i) =>
        node(
          "label",
          null,
          name,
          input(
            {
              type: "number",
              "aria-label": "Festivos " + name,
              min: 0,
              max: 31,
              value: state.holidays[i] || 0,
            },
            (v) => actions.holiday(i, v),
          ),
        ),
      ),
    ),
  );
  state.rows = model.monthlyRows();
  const sections = [
    ["general", "Información general", "calendar", []],
    ["hours", "Horas registradas", "money", []],
    ["cats", "Detalle por concepto", "layers", []],
    ["pcts", "Porcentajes", "target", []],
    ["final", "Indicadores finales", "bars", []],
  ];
  for (const row of state.rows) {
    const label = row[0],
      at = ["Facturabilidad", "Capacidad", "Clientes Internos"].includes(label)
        ? 4
        : label.startsWith("% ")
          ? 3
          : label === "Total horas registradas"
            ? 1
            : cats.includes(label)
              ? 2
              : 0;
    sections[at][3].push(row);
  }
  const rows = [];
  for (const [id, title, symbol, data] of sections) {
    const b = button("", () => actions.toggle("areaCollapsed", id), "", {
      "aria-expanded": String(!selection.areaCollapsed.has(id)),
    });
    b.append(
      icon(symbol),
      title,
      text("span", selection.areaCollapsed.has(id) ? "⌄" : "⌃"),
    );
    rows.push(
      node(
        "tr",
        "ga-section",
        Object.assign(node("th", null, b), { colSpan: 13 }),
      ),
    );
    if (selection.areaCollapsed.has(id)) continue;
    for (const row of data) {
      const label = row[0],
        percent = id === "pcts" || id === "final";
      if (selection.areaPercent && id === "cats") continue;
      rows.push(
        node(
          "tr",
          label === "Capacidad horas al mes" ? "gm-grand" : "",
          text("th", label),
          row.slice(1).map((v) => {
            const n = typeof v === "number" ? v : null,
              color =
                percent && n != null
                  ? n > 100
                    ? "gm-red"
                    : n >= 80
                      ? "gm-green"
                      : n >= 60
                        ? "gm-amber"
                        : "ga-low"
                  : "";
            return cell(n == null ? v : n, color, percent);
          }),
        ),
      );
    }
  }
  const table = node(
    "table",
    "gm-table ga-table",
    node(
      "thead",
      null,
      node(
        "tr",
        null,
        ["Concepto", ...months].map((m) => text("th", m)),
      ),
    ),
    node("tbody", null, rows),
  );
  return [
    cards,
    node(
      "div",
      "ga-info",
      icon("info"),
      node(
        "span",
        null,
        "Área: ",
        text("b", state.area),
        ". Los indicadores usan " +
          period +
          ". Las categorías pueden solaparse; recursos cuenta personas con horas en el mes.",
      ),
    ),
    charts,
    holidays,
    node(
      "section",
      "gm-card ga-report",
      node(
        "header",
        null,
        node(
          "div",
          null,
          heading("Resumen mensual · " + state.area + " · " + state.year),
          text(
            "p",
            "Horas, capacidad, facturabilidad y recursos por mes.",
            "ga-sub",
          ),
        ),
        node(
          "div",
          "gm-switch",
          button(
            "Absolutos",
            () => actions.set("areaPercent", false),
            !selection.areaPercent ? "active" : "",
          ),
          button(
            "Porcentajes",
            () => actions.set("areaPercent", true),
            selection.areaPercent ? "active" : "",
          ),
        ),
      ),
      node("div", "gm-table-scroll", table),
    ),
    node(
      "details",
      "gm-card gm-method",
      node("summary", null, icon("info"), " Notas y metodología"),
      text(
        "p",
        "Capacidad mensual = personas con horas × jornada diaria × días laborables. Los festivos se editan en la tarjeta situada encima de la tabla. Los porcentajes se calculan sobre la capacidad mensual. Las categorías pueden solaparse; las columnas de la gráfica representan la suma de los conceptos mostrados, no el total de horas registradas. Recursos por concepto cuenta cada persona una sola vez en cada concepto. NA indica mes sin datos disponibles.",
      ),
    ),
  ];
}
