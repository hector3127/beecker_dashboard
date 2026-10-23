import { months, cats, colors, num } from "./model.js";
import {
  el,
  node,
  text,
  styled,
  button,
  icon,
  heading,
  track,
  monthSelect,
  cell,
} from "./ui.js";

export function overview(state, selection, model, actions) {
  const {
    valid,
    list,
    people,
    has,
    pct,
    percentage,
    sumCat,
    sumHours,
    monthly,
    capacity,
    total,
    fact,
    nonfact,
    other,
  } = model.overview();
  const { workdays } = model,
    oper = pct(fact, capacity),
    bill = pct(fact, total);
  const spark = (values, color) =>
    node(
      "span",
      "gm-spark",
      values.map((v) =>
        styled("i", null, {
          height:
            Math.max(
              3,
              (25 * (Number(v) || 0)) /
                Math.max(1, ...values.map((x) => Number(x) || 0)),
            ) + "px",
          background: color,
        }),
      ),
    );
  const metric = (label, value, symbol, values, color) =>
    node(
      "article",
      "gm-kpi",
      node(
        "div",
        "gm-kpi-label",
        styled("span", "gm-icon", { color }, icon(symbol)),
        text("span", label),
      ),
      text("strong", value),
      spark(values, color),
    );
  const cards = node(
    "div",
    "gm-kpis",
    metric(
      "Facturabilidad operativa",
      has ? percentage(oper) : "NA",
      "target",
      monthly.map((a, i) =>
        a
          ? pct(
              a.categorias.Facturable || 0,
              workdays(i) * state.day * a.recursos,
            )
          : 0,
      ),
      "#7944ef",
    ),
    metric(
      "Horas facturables / registradas",
      has ? percentage(bill) : "NA",
      "money",
      monthly.map((a) => (a ? pct(a.categorias.Facturable || 0, a.horas) : 0)),
      "#7944ef",
    ),
    metric(
      "Capacidad total (h)",
      has ? num(capacity) : "NA",
      "bars",
      monthly.map((a, i) => (a ? workdays(i) * state.day * a.recursos : 0)),
      "#80a5ff",
    ),
    metric(
      "Horas facturables",
      has ? num(fact) : "NA",
      "money",
      monthly.map((a) => a?.categorias.Facturable || 0),
      "#9e77f3",
    ),
    metric(
      "Horas de pre-venta",
      has ? num(other) : "NA",
      "target",
      monthly.map((a) => a?.categorias["Pre-Venta"] || 0),
      "#f4c253",
    ),
    metric(
      "Recursos únicos",
      has ? num(people.size) : "NA",
      "people",
      monthly.map((a) => a?.recursos || 0),
      "#9e77f3",
    ),
    node(
      "article",
      "gm-kpi gm-legend",
      node("b", null, icon("check"), " Facturabilidad mensual"),
      [
        ["#28ba7b", " ≥ 80%"],
        ["#efa72a", " 60–79%"],
        ["#ea426a", " < 60%"],
      ].map(([color, label]) =>
        node("span", null, styled("i", null, { background: color }), label),
      ),
    ),
  );
  state.rows = [];
  const row = (label, values, opts = {}) => {
    state.rows.push([
      label instanceof Node ? label.textContent : label,
      ...values.map((v) => (v == null ? "NA" : v)),
      opts.total == null ? "NA" : opts.total,
    ]);
    return styled(
      "tr",
      opts.class,
      opts.color ? { "--area-color": opts.color } : {},
      node("th", null, label),
      ...values.map((v) =>
        cell(
          v,
          opts.heat && v != null
            ? v >= 80
              ? "gm-green"
              : v >= 60
                ? "gm-amber"
                : "gm-red"
            : "",
          opts.percent,
        ),
      ),
      cell(opts.total, "gm-total", opts.percent),
    );
  };
  const rows = [
    row(
      node("span", null, icon("calendar"), " Calendario"),
      months.map((_, i) => "01-" + String(i + 1).padStart(2, "0")),
      { class: "gm-calendar", total: state.year },
    ),
    row(
      "Días laborables",
      months.map((_, i) => workdays(i)),
      { total: months.reduce((n, _, i) => n + workdays(i), 0) },
    ),
    row(
      "Horas por recurso",
      months.map((_, i) => workdays(i) * state.day),
      { total: months.reduce((n, _, i) => n + workdays(i) * state.day, 0) },
    ),
  ];
  // The calendar icon was adjacent to the label in the original table.
  rows[0].firstChild.replaceChildren(icon("calendar"), " Calendario");
  const iconArea = (name) =>
    /sm|scrum/i.test(name)
      ? "people"
      : /arqu/i.test(name)
        ? "layers"
        : /test|calidad|pract/i.test(name)
          ? "flask"
          : /dev|desarr/i.test(name)
            ? "gear"
            : "people";
  list.forEach((a, index) => {
    const color = colors[index % colors.length],
      expanded = selection.expanded.has(a.name),
      cap = a.months.reduce(
        (n, m, i) => n + (m ? workdays(i) * state.day * m.recursos : 0),
        0,
      );
    const label = button(
      "",
      () => actions.toggle("expanded", a.name),
      "gm-area-button",
      { "aria-expanded": String(expanded) },
    );
    label.append(
      text("span", expanded ? "⌄" : "›", "gm-chevron"),
      icon(iconArea(a.name)),
      " " + a.name,
    );
    rows.push(
      row(
        label,
        a.months.map((m, i) =>
          m
            ? selection.displayPercent
              ? pct(m.horas, workdays(i) * state.day * m.recursos)
              : m.horas
            : valid[i]
              ? 0
              : null,
        ),
        {
          class: "gm-area",
          color,
          total: selection.displayPercent ? pct(sumHours(a), cap) : sumHours(a),
          percent: selection.displayPercent,
        },
      ),
    );
    if (expanded)
      for (const cat of cats)
        rows.push(
          row(
            cat,
            a.months.map((m, i) =>
              !m
                ? valid[i]
                  ? 0
                  : null
                : m.categorias[cat] === null
                  ? null
                  : selection.displayPercent
                    ? pct(
                        m.categorias[cat] || 0,
                        workdays(i) * state.day * m.recursos,
                      )
                    : m.categorias[cat] || 0,
            ),
            {
              class: "gm-category",
              total: selection.displayPercent
                ? pct(sumCat(a, cat), cap)
                : sumCat(a, cat),
              percent: selection.displayPercent,
            },
          ),
        );
  });
  rows.push(
    row(
      "Σ Total general",
      monthly.map((a, i) =>
        a
          ? selection.displayPercent
            ? pct(a.horas, workdays(i) * state.day * a.recursos)
            : a.horas
          : null,
      ),
      {
        class: "gm-grand",
        total: has
          ? selection.displayPercent
            ? pct(total, capacity)
            : total
          : null,
        percent: selection.displayPercent,
      },
    ),
    row(
      "% Facturabilidad global",
      monthly.map((a, i) =>
        a
          ? pct(
              a.categorias.Facturable === null
                ? null
                : a.categorias.Facturable || 0,
              workdays(i) * state.day * a.recursos,
            )
          : null,
      ),
      { total: has ? oper : null, percent: true, heat: true },
    ),
  );
  const switcher = node(
    "div",
    "gm-switch",
    button(
      "Horas",
      () => actions.set("displayPercent", false),
      !selection.displayPercent ? "active" : "",
    ),
    button(
      "% de capacidad",
      () => actions.set("displayPercent", true),
      selection.displayPercent ? "active" : "",
    ),
  );
  const table = node(
    "table",
    "gm-table",
    node(
      "thead",
      null,
      node(
        "tr",
        null,
        ["Área / Concepto", ...months.map((m) => m.slice(0, 3)), "Total"].map(
          (h) => text("th", h),
        ),
      ),
    ),
    node("tbody", null, rows),
  );
  const progress = (label, value, max, color, extra) =>
    node(
      "div",
      "gm-progress",
      node("div", null, text("span", label), text("b", num(value))),
      track(Math.min(100, max ? (value / max) * 100 : 0), color),
      text("small", extra),
    );
  const ranking = (title, symbol, values) =>
    node(
      "section",
      "gm-card",
      node("h3", null, icon(symbol), " ", title),
      values.map((x, i) =>
        node(
          "div",
          "gm-rank",
          text("span", x.name),
          text("b", num(x.value)),
          track(
            values[0]?.value ? (100 * x.value) / values[0].value : 0,
            colors[i % colors.length],
          ),
        ),
      ),
      !values.length
        ? text("p", "Consulta el año para mostrar los datos.", "gse-note")
        : null,
    );
  const peopleTitle = document.createDocumentFragment();
  peopleTitle.append(
    "Recursos únicos por área ",
    monthSelect(
      selection.peopleMonth,
      (v) => actions.set("peopleMonth", Number(v)),
      { "aria-label": "Mes de recursos por área" },
    ),
  );
  return [
    cards,
    node(
      "div",
      "gm-layout",
      node(
        "section",
        "gm-card gm-main",
        node(
          "header",
          null,
          heading("Horas por área y concepto", "layers"),
          switcher,
        ),
        node("div", "gm-table-scroll", table),
      ),
      node(
        "aside",
        "gm-aside",
        node(
          "section",
          "gm-card",
          heading("Resumen anual " + state.year),
          progress(
            "Capacidad (h)",
            capacity,
            Math.max(capacity, total),
            "#7542ef",
            "Suma de capacidad de los meses cargados",
          ),
          progress(
            "Horas registradas",
            total,
            Math.max(capacity, total),
            "#9166ef",
            percentage(pct(total, capacity)) + " de capacidad",
          ),
          progress(
            "Horas facturables",
            fact,
            Math.max(total, fact),
            "#7542ef",
            percentage(bill) + " de horas registradas",
          ),
          progress(
            "Horas no facturables",
            nonfact,
            Math.max(total, nonfact),
            "#efaf35",
            percentage(pct(nonfact, total)) + " de horas registradas",
          ),
        ),
        ranking(
          "Volumen de horas por área",
          "clock",
          list
            .map((a) => ({ name: a.name, value: sumHours(a) }))
            .sort((a, b) => b.value - a.value),
        ),
        ranking(
          peopleTitle,
          "people",
          list
            .map((a) => ({
              name: a.name,
              value:
                selection.peopleMonth < 0
                  ? a.people.size
                  : a.months[selection.peopleMonth]?.recursos || 0,
            }))
            .sort((a, b) => b.value - a.value),
        ),
      ),
    ),
    node(
      "details",
      "gm-card gm-method",
      node("summary", null, icon("info"), " Notas y metodología"),
      text(
        "p",
        "Capacidad: personas con horas × jornada diaria × días laborables. Recursos únicos cuenta personas con registros en los meses cargados; no representa FTE. Facturabilidad operativa = horas facturables / capacidad. La segunda tarjeta compara horas facturables con horas registradas. Las categorías pueden solaparse y no deben sumarse como una partición del total. Las horas de pre-venta se muestran por separado. NA indica mes sin datos disponibles.",
      ),
      text(
        "p",
        "Los datos parciales se indican en el avance superior. No se muestran tendencias ni variaciones sin un período comparable.",
      ),
    ),
  ];
}
