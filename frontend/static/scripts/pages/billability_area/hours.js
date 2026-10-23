import { months, num, norm } from "./model.js";
import { el, node, text, styled, button, input, select, icon } from "./ui.js";

export function hoursDetail(state, selection, model, actions) {
  const {
    HIDDEN,
    ALL,
    valid,
    byPerson,
    sums,
    roles,
    rows,
    yearOf,
    YEAR_COLS,
    monthCols,
    label,
    round,
    blank,
  } = model.hoursDetail();
  const full = yearOf(sums.filter((_, i) => valid[i])),
    pct = (v, t) => (t ? round((100 * v) / t) + "%" : "NA");
  const kpi = (symbol, cls, name, value, note, ratio) =>
    node(
      "article",
      "ghr-kpi " + cls,
      node(
        "div",
        "ghr-kpi-main",
        node("span", "ghr-kpi-icon", icon(symbol)),
        node(
          "div",
          null,
          text("small", name),
          text("b", value),
          text("em", note),
        ),
      ),
      el(
        "div",
        {
          class: "ghr-kpi-bar",
          role: "img",
          "aria-label":
            Math.round(Math.max(0, Math.min(1, ratio || 0)) * 100) + "%",
        },
        styled("i", null, {
          width: Math.max(0, Math.min(1, ratio || 0)) * 100 + "%",
        }),
      ),
    );
  const loaded = valid.filter(Boolean).length,
    roster = (state.resourceBands || []).length || byPerson.size;
  const cards = node(
    "section",
    "ghr-kpis",
    kpi(
      "clock",
      "ghr-k1",
      "Horas registradas",
      num(full.total),
      "Total " + state.year,
      loaded / months.length,
    ),
    kpi(
      "layers",
      "ghr-k2",
      "AER",
      num(full.AER),
      pct(full.AER, full.total) + " del total",
      full.total ? full.AER / full.total : 0,
    ),
    kpi(
      "bars",
      "ghr-k3",
      "Servicios (TYM, IxB, SaaS, RaaS)",
      num(full.svc),
      pct(full.svc, full.total) + " del total",
      full.total ? full.svc / full.total : 0,
    ),
    kpi(
      "people",
      "ghr-k4",
      "Recursos con horas",
      String(byPerson.size),
      state.area || "Todas las áreas",
      roster ? Math.min(1, byPerson.size / roster) : 0,
    ),
  );
  const options = (items, all) => [["", all], ...items.map((v) => [v, v])];
  const filters = node(
    "section",
    "ghr-filters",
    node(
      "label",
      null,
      "Rol",
      select(
        options(
          Array.from(roles).sort((a, b) => a.localeCompare(b, "es")),
          "Todos",
        ),
        selection.hoursRole,
        (v) => actions.set("hoursRole", v),
      ),
    ),
    node(
      "label",
      null,
      "Servicio",
      select(options(ALL, "Todos"), selection.hoursService, (v) =>
        actions.set("hoursService", v),
      ),
    ),
    node(
      "div",
      "ghr-search",
      icon("search"),
      input(
        {
          id: "gse-hours-search",
          type: "search",
          value: selection.hoursSearch,
          placeholder: "Buscar recurso...",
        },
        (v) => actions.set("hoursSearch", v, "gse-hours-search"),
        "input",
      ),
    ),
    node(
      "div",
      "ghr-actions",
      button(
        "Ver todos los servicios",
        () => actions.hoursAll(true),
        "ghr-btn",
      ),
      button("Contraer meses", () => actions.hoursAll(false), "ghr-btn"),
      button("", () => exportHours(state), "ghr-btn ghr-primary"),
    ),
  );
  filters.querySelector(".ghr-primary").append(icon("download"), " Exportar");
  const th = (f, cls) =>
    el("th", {
      class:
        "ghr-sub " +
        cls +
        (HIDDEN.includes(f) ? " ghr-extra" : "") +
        (f === "svc" ? " ghr-svc" : ""),
      title: f === "svc" ? "TYM + IxB + SaaS + RaaS" : null,
      text: label(f),
    });
  const td = (c, f, cls) =>
    el("td", {
      class:
        cls +
        (HIDDEN.includes(f) ? " ghr-extra" : "") +
        (f === "svc" ? " ghr-svc" : "") +
        (c && !c[f] ? " ghr-zero" : ""),
      "data-value": c ? round(c[f]) : "",
      text: c ? num(c[f]) : "NA",
    });
  const monthHead = (m, i) => {
    const open = selection.hoursOpen.has(i);
    return el(
      "th",
      { class: "ghr-group ghr-m" + i, colspan: monthCols(i).length },
      text("span", m),
      button(
        open ? "‹" : "›",
        () => actions.toggle("hoursOpen", i),
        "ghr-toggle",
        {
          "aria-expanded": String(open),
          "aria-label":
            (open ? "Ocultar" : "Ver") + " TYM, IxB, SaaS y RaaS de " + m,
          title: (open ? "Ocultar" : "Ver") + " TYM, IxB, SaaS y RaaS",
        },
      ),
    );
  };
  const bajas = model.bajas(),
    dataRows = rows.map((r) => {
      const low = bajas.has(norm(r.name).replace(/\s+/g, " ")),
        mark = low ? " gse-baja" : "";
      return node(
        "tr",
        null,
        text("th", r.area, "ghr-rol" + mark),
        text("th", r.name, "ghr-name" + mark),
        YEAR_COLS.map((f) => td(yearOf(r.m), f, "ghr-year")),
        months.map((_, i) => {
          const c = r.m[i] || (valid[i] ? blank() : null);
          return monthCols(i).map((f) => td(c, f, ""));
        }),
      );
    });
  if (!rows.length)
    dataRows.push(
      node(
        "tr",
        null,
        el("td", {
          class: "ghr-empty",
          colspan:
            2 +
            YEAR_COLS.length +
            months.reduce((n, _, i) => n + monthCols(i).length, 0),
          text: "Sin horas para mostrar. Consulta un año o ajusta los filtros.",
        }),
      ),
    );
  const share = (c, total, f, cls = "") =>
    text(
      "td",
      c && total ? pct(c[f], total.total) : "NA",
      cls +
        (HIDDEN.includes(f) ? "ghr-extra " : "") +
        (f === "svc" ? "ghr-svc " : ""),
    );
  const table = el(
    "table",
    { id: "gse-hours-table", class: "ghr-table" },
    node(
      "thead",
      null,
      node(
        "tr",
        null,
        el("th", { rowspan: 2, class: "ghr-rol", text: "ROL" }),
        el("th", { rowspan: 2, class: "ghr-name", text: "Recurso" }),
        el("th", {
          class: "ghr-group ghr-year",
          colspan: YEAR_COLS.length,
          text: "Total " + state.year,
        }),
        months.map(monthHead),
      ),
      node(
        "tr",
        null,
        YEAR_COLS.map((f) => th(f, "ghr-year")),
        months.map((_, i) => monthCols(i).map((f) => th(f, "ghr-m" + i))),
      ),
    ),
    node("tbody", null, dataRows),
    node(
      "tfoot",
      null,
      node(
        "tr",
        "ghr-total",
        text("th", "", "ghr-rol"),
        text("th", "Total de horas", "ghr-name"),
        YEAR_COLS.map((f) => td(full, f, "ghr-year")),
        months.map((_, i) =>
          monthCols(i).map((f) => td(valid[i] ? sums[i] : null, f, "")),
        ),
      ),
      node(
        "tr",
        "ghr-share",
        text("th", "", "ghr-rol"),
        text("th", "% del total", "ghr-name"),
        YEAR_COLS.map((f) => share(full, full, f, "ghr-year ")),
        months.map((_, i) =>
          monthCols(i).map((f) => share(valid[i] ? sums[i] : null, sums[i], f)),
        ),
      ),
    ),
  );
  return [
    cards,
    filters,
    node("section", "ghr-card", node("div", "ghr-scroll", table)),
  ];
}
function exportHours(state) {
  const table = document.getElementById("gse-hours-table");
  if (!table) return;
  const rows = Array.from(table.querySelectorAll("tr")).map((tr) =>
    Array.from(tr.children)
      .map((c) => {
        const n = Number(c.dataset.value);
        return c.dataset.value !== undefined &&
          c.dataset.value !== "" &&
          !isNaN(n)
          ? String(n)
          : '"' + c.textContent.trim().replace(/"/g, '""') + '"';
      })
      .join(","),
  );
  const url = URL.createObjectURL(
      new Blob(["\uFEFF" + rows.join("\n")], {
        type: "text/csv;charset=utf-8",
      }),
    ),
    a = el("a", {
      href: url,
      download: "gse_detalle_hrs_" + state.year + ".csv",
    });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
