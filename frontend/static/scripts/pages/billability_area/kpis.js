import { months, num } from "./model.js";
import {
  el,
  node,
  text,
  styled,
  input,
  select,
  monthSelect,
  icon,
  heading,
  track,
  table,
  cell,
  svg,
  legend,
} from "./ui.js";

const chartColors = [
  "#7737ed",
  "#ff713b",
  "#ffc322",
  "#448bff",
  "#26bd81",
  "#29bfd9",
];
function lineChart(rows, max, labels) {
  const chart = svg("svg", {
    viewBox: "0 0 420 210",
    role: "img",
    "aria-label": "Gráfica mensual",
  });
  for (let t = 0; t <= 4; t++) {
    const y = 175 - (150 * t) / 4;
    chart.append(
      svg("path", { d: "M35 " + y + "H410", stroke: "#eeeafa" }),
      svg(
        "text",
        {
          x: 30,
          y: y + 3,
          "text-anchor": "end",
          "font-size": 10,
          fill: "#8a80a0",
        },
        num((max * t) / 4),
      ),
    );
  }
  rows.forEach((values, j) => {
    let segment = [];
    const flush = () => {
      if (segment.length)
        chart.append(
          svg("polyline", {
            points: segment.join(" "),
            fill: "none",
            stroke: chartColors[j],
            "stroke-width": 2,
          }),
        );
      segment = [];
    };
    values.forEach((v, i) => {
      if (v == null) {
        flush();
        return;
      }
      const x = 40 + i * 33,
        y = 175 - (150 * v) / max;
      segment.push(x + "," + y);
      chart.append(
        svg(
          "circle",
          { cx: x, cy: y, r: 3, fill: chartColors[j] },
          svg("title", {}, months[i] + ": " + num(v)),
        ),
      );
    });
    flush();
  });
  months.forEach((m, i) =>
    chart.append(
      svg(
        "text",
        {
          x: 40 + i * 33,
          y: 197,
          "text-anchor": "middle",
          "font-size": 9,
          fill: "#8a80a0",
        },
        m.slice(0, 3),
      ),
    ),
  );
  return [chart, legend(labels.map((l, j) => [l, chartColors[j]]))];
}
export function kpis(state, selection, model, actions) {
  const {
    d,
    monthly,
    valid,
    people,
    employeeNames,
    services,
    sum,
    total,
    pct,
    f,
    p,
    period,
    latest,
    variation,
    fact,
    maturity,
    annualFact,
    annualCapacity,
  } = model.kpiSummary();
  const card = (label, value, symbol, color, note) =>
    node(
      "article",
      "gm-kpi",
      node(
        "div",
        "gm-kpi-label",
        styled("span", "gm-icon", { color }, icon(symbol)),
        label,
      ),
      styled("strong", null, { color }, value),
      text("small", note),
      track(65, color),
    );
  const header = node(
    "header",
    "gse-resource-heading",
    node(
      "div",
      null,
      text("h2", "GSE · KPIs operativos"),
      text(
        "p",
        (state.area || "Todas las áreas") +
          " · " +
          state.year +
          " · Datos ya cargados",
        "gse-note",
      ),
    ),
  );
  const controls = node(
    "div",
    "gse-tools",
    node(
      "label",
      null,
      "Empleado",
      select(
        [
          ["", "Todos los empleados"],
          ...Array.from(employeeNames).sort((a, b) =>
            a[1].localeCompare(b[1], "es"),
          ),
        ],
        selection.kpiPerson,
        (v) => actions.set("kpiPerson", v),
      ),
    ),
    node(
      "label",
      null,
      "Mes",
      monthSelect(selection.kpiMonth, (v) =>
        actions.set("kpiMonth", Number(v)),
      ),
    ),
    node(
      "label",
      null,
      "Objetivo editable (%)",
      input(
        { type: "number", min: 0, max: 100, value: selection.kpiTarget },
        (v) =>
          actions.set("kpiTarget", Math.min(100, Math.max(0, Number(v) || 0))),
      ),
    ),
  );
  const cards = node(
    "div",
    "gk-kpis",
    card(
      "Facturabilidad · " + period,
      p(fact),
      "bars",
      "#20b779",
      "Facturables / capacidad del período",
    ),
    card(
      "Facturabilidad anual",
      p(pct(annualFact, annualCapacity)),
      "target",
      "#eda321",
      "Facturables / capacidad anual",
    ),
    card(
      "Madurez operativa",
      f(maturity),
      "layers",
      "#7438ed",
      maturity == null
        ? "Sin datos"
        : maturity <= 2
          ? "Repetitivo / operativo"
          : maturity <= 4
            ? "Escalable"
            : "Innovador / SaaS",
    ),
    card(
      "Variación mensual",
      p(variation),
      "bars",
      variation >= 0 ? "#20b779" : "#e14b65",
      latest != null
        ? months[latest] + " vs. mes anterior"
        : "Sin período comparable",
    ),
  );
  const info = node(
    "section",
    "ga-info",
    icon("info"),
    node(
      "span",
      null,
      "Facturabilidad identificada: " +
        f(sum("fact")) +
        " h / " +
        f(total) +
        " h registradas. Sin clasificación: ",
      text("b", f(d.unknown) + " h"),
      ". Estas horas permanecen en el total; no se asignan a no facturables. " +
        (d.unknown > 0
          ? "El porcentaje puede aumentar al completar la clasificación."
          : "Clasificación completa para el período."),
    ),
  );
  const fields = ["fact", "non", "carg", "nocarg", "affect", "noaffect"],
    oper = fields.map((field) =>
      monthly.map((m, i) =>
        valid[i] && m.total ? pct(m[field], m.total) : null,
      ),
    );
  const bars = svg("svg", {
      viewBox: "0 0 420 210",
      role: "img",
      "aria-label": "Horas por servicio",
    }),
    max = Math.max(1, ...monthly.map((m) => m.total));
  monthly.forEach((m, i) => {
    let y = 175;
    services.forEach((s, j) => {
      const h = (m.svc[s] / max) * 150;
      y -= h;
      bars.append(
        svg(
          "rect",
          { x: 38 + i * 32, y, width: 21, height: h, fill: chartColors[j] },
          svg("title", {}, months[i] + " · " + s + ": " + f(m.svc[s])),
        ),
      );
    });
    bars.append(
      svg(
        "text",
        {
          x: 48 + i * 32,
          y: 197,
          "text-anchor": "middle",
          "font-size": 9,
          fill: "#8a80a0",
        },
        months[i].slice(0, 3),
      ),
    );
  });
  const maturityNote = node(
    "p",
    "ga-sub",
    "Operativo ≤ 2 · Escalable > 2 y ≤ 4 · Innovador > 4",
    el("br"),
    "SaaS 6 · RaaS 5 · AER 4 · IxB 3 · TYM 2 · Otros 1",
  );
  const charts = node(
    "div",
    "gk-charts",
    node(
      "section",
      "gm-card",
      heading("Estatus operativo"),
      lineChart(oper, 100, [
        "Facturable",
        "No facturable",
        "Cargable",
        "No cargable",
        "Afecta capacidad",
        "No afecta",
      ]),
    ),
    node(
      "section",
      "gm-card",
      heading("Índice de evolución operativa", "target"),
      lineChart(
        [
          monthly.map((m, i) =>
            valid[i] && m.total ? m.weighted / m.total : null,
          ),
        ],
        6,
        ["Índice ponderado"],
      ),
      maturityNote,
    ),
    node(
      "section",
      "gm-card",
      heading("Distribución de horas por servicio", "layers"),
      bars,
      legend(services.map((s, j) => [s, chartColors[j]])),
    ),
  );
  const heat = (v) =>
      v == null
        ? ""
        : v >= selection.kpiTarget
          ? "gm-green"
          : v >= selection.kpiTarget * 0.75
            ? "gm-amber"
            : "gm-red",
    annual = [],
    planner = [],
    bajas = model.bajas();
  for (const person of people.values()) {
    const low = bajas.has(d.normalize(person.name)),
      values = person.months.filter(Boolean),
      sumP = (k) => values.reduce((n, m) => n + m[k], 0),
      tot = sumP("total"),
      bill = sumP("fact"),
      non = sumP("non"),
      other = Math.max(0, tot - (bill || 0) - (non || 0)),
      personCapacity = person.months.reduce(
        (n, m, i) => n + (m ? state.day * model.workdays(i) : 0),
        0,
      );
    annual.push(
      node(
        "tr",
        null,
        text("th", person.name, low ? "gse-baja" : ""),
        [
          bill,
          non,
          sumP("invop"),
          sumP("invcom"),
          other,
          tot,
          personCapacity,
        ].map((v) => text("td", f(v))),
        node(
          "td",
          heat(pct(bill, personCapacity)),
          text(
            "span",
            p(bill == null ? null : pct(bill, personCapacity)),
            "gk-pill",
          ),
        ),
      ),
    );
    planner.push(
      node(
        "tr",
        null,
        text("th", person.name, low ? "gse-baja" : ""),
        person.months.map((m, i) => {
          const v = m
            ? pct(m.fact, state.day * model.workdays(i))
            : valid[i]
              ? 0
              : null;
          return text("td", p(v), heat(v));
        }),
      ),
    );
  }
  const serviceRows = services.map((s) =>
    node(
      "tr",
      null,
      text("th", s),
      monthly.map((m, i) =>
        text(
          "td",
          valid[i] ? f(m.svc[s]) : "NA",
          valid[i]
            ? m.svc[s] >= Math.max(1, ...monthly.map((x) => x.svc[s])) * 0.66
              ? "gm-green"
              : m.svc[s] >= Math.max(1, ...monthly.map((x) => x.svc[s])) * 0.33
                ? "gm-amber"
                : "gm-red"
            : "",
        ),
      ),
    ),
  );
  const report = (title, heads, rows) =>
    node(
      "section",
      "gm-card",
      heading(title, "people"),
      node("div", "gm-table-scroll", table(heads, rows)),
    );
  planner.push(
    node(
      "tr",
      "gk-objective",
      text("th", "Objetivo editable"),
      months.map(() => text("td", selection.kpiTarget + "%")),
    ),
  );
  const bottom = node(
    "div",
    "gk-bottom",
    node(
      "div",
      null,
      report(
        "Anual empleado",
        [
          "Empleado",
          "Facturable",
          "No facturable",
          "Inv. operativa",
          "Inv. comercial",
          "Sin clasificar",
          "Registradas h",
          "Total Hrs (capacidad)",
          "% útil",
        ],
        annual,
      ),
    ),
    node(
      "div",
      null,
      report(
        "Mensual por servicio · " + (state.area || "Todas las áreas"),
        ["Servicio / Mes", ...months.map((m) => m.slice(0, 3))],
        serviceRows,
      ),
      report(
        "Planeador de capacidad facturable",
        ["Empleado / Mes", ...months.map((m) => m.slice(0, 3))],
        planner,
      ),
    ),
  );
  return el(
    "div",
    { id: "gse-kpi-modal", class: "gse-inline-view" },
    el(
      "section",
      {
        class: "gse-resource-dialog gk-dialog",
        role: "dialog",
        "aria-modal": "true",
        "aria-label": "KPIs GSE",
      },
      el(
        "div",
        { id: "gse-kpi-body" },
        header,
        controls,
        cards,
        info,
        charts,
        bottom,
        node(
          "section",
          "ga-info",
          icon("info"),
          text(
            "span",
            "Facturabilidad del período = horas facturables / capacidad del período. Con Todos los meses coincide con la anual. Facturabilidad anual = suma de facturables / suma de Total Hrs (capacidad) de empleados. Planeador = facturables / capacidad laboral. Administrativo y Sin Asignación son no cargables; Optimización no afecta capacidad. Inversiones son desgloses que pueden formar parte de otras columnas; no se suman otra vez. El objetivo es editable y no proviene de Sheets. Las horas sin clasificación se muestran por separado y no anulan los datos identificados. NA indica ausencia de horas en el período. Las gráficas y tablas conservan los 12 meses para comparar; el selector cambia los KPIs del período.",
          ),
        ),
      ),
    ),
  );
}
