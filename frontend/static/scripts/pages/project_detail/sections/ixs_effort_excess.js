import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";
import { num, dateText } from "./ixs_executive_model.js";
import { h, div, empty } from "./ixs_executive_view.js";
import { button, dateInput } from "./ixs_effort_clockify.js";

const b = (text) => h("b", "", text),
  small = (text) => h("small", "", text);

export function excessDialog(records, actions) {
  document.getElementById("ixs-excess-modal")?.remove();
  const days = (records || [])
    .filter((x) => x.billable === true)
    .map((x) => x.fecha)
    .filter(Boolean)
    .sort();
  const dialog = el(
    "dialog",
    { id: "ixs-excess-modal", class: "ixs-excess-dialog" },
    h(
      "header",
      "ex-header",
      div(
        "ex-heading",
        h(
          "h2",
          "",
          h("span", "ex-warning", icon("warning")),
          "Registros fuera de las horas estimadas",
        ),
        h(
          "p",
          "",
          "Por persona, en orden de fecha e inicio. Solo horas facturables, incluidas las que no tienen task. El registro que cruza el límite muestra solo su parte excedida.",
        ),
      ),
      div(
        "ex-controls",
        dateInput("ixs-excess-from", "Fecha inicio", days[0] || ""),
        dateInput("ixs-excess-to", "Fecha fin", days[days.length - 1] || ""),
        button("Aplicar fechas", actions.filter, "ixs-btn primary"),
        button("↓ Exportar CSV", actions.export, "ixs-btn", {
          id: "ixs-excess-export",
        }),
        button("✕", actions.close, "ex-close", {
          "aria-label": "Cerrar ventana",
        }),
      ),
    ),
    el("div", { id: "ixs-excess-records" }),
  );
  document.body.append(dialog);
  dialog.addEventListener("close", () => dialog.remove());
  dialog.showModal();
  return dialog;
}

export function renderExcess(
  state,
  people,
  pagesByPerson,
  sortByPerson,
  actions,
) {
  const target = document.getElementById("ixs-excess-records");
  if (!target) return;
  const exportButton = document.getElementById("ixs-excess-export");
  if (exportButton) exportButton.disabled = state.cargando || !!state.error;
  if (state.cargando) {
    target.replaceChildren(empty("Consultando registros…"));
    return;
  }
  if (state.error) {
    target.textContent = state.error;
    return;
  }
  if (exportButton) exportButton.disabled = !people.length;
  const existing = [...target.querySelectorAll("details[data-ex-person]")],
    opened = new Set(
      existing.filter((x) => x.open).map((x) => Number(x.dataset.exPerson)),
    );
  target.replaceChildren(
    ...(people.length
      ? people.map((p, i) => {
          const sort = sortByPerson[i] || { field: "fecha", dir: 1 },
            records = [...p.records].sort(
              (a, b) =>
                sort.dir *
                  String(a[sort.field] || "").localeCompare(
                    String(b[sort.field] || ""),
                  ) ||
                String(a.fecha + " " + a.inicio).localeCompare(
                  String(b.fecha + " " + b.inicio),
                ),
            );
          const pages = Math.ceil(records.length / 8),
            page = Math.min(pages, Math.max(1, pagesByPerson[i] || 1)),
            start = (page - 1) * 8,
            visible = records.slice(start, start + 8);
          const heading = (label, field) =>
            el(
              "th",
              {
                "aria-sort":
                  sort.field === field
                    ? sort.dir === 1
                      ? "ascending"
                      : "descending"
                    : "none",
              },
              button(
                [
                  label + " ",
                  el(
                    "span",
                    { "aria-hidden": "true" },
                    sort.field === field ? (sort.dir === 1 ? "↑" : "↓") : "↕",
                  ),
                ],
                () => actions.sort(i, field),
                "ex-sort",
              ),
            );
          const numbers = Array.from({ length: pages }, (_, n) => n + 1).filter(
            (n) => n === 1 || n === pages || Math.abs(n - page) <= 2,
          );
          const metric = (name, label, value, cls = "") =>
            h(
              "span",
              `ex-metric ${cls}`,
              icon(name),
              " " + label + " ",
              b(num(value, 2) + " h"),
            );
          const td = (value) => h("td", "", value);
          return el(
            "details",
            {
              "data-ex-person": i,
              open: existing.length ? opened.has(i) : i === 0,
            },
            h(
              "summary",
              "",
              h("span", "ex-avatar", icon("people")),
              div("ex-person", b(p.name), small(p.role)),
              metric("clock", "Estimadas", p.budget),
              metric("clock", "Consumidas", p.used),
              metric(
                "warning",
                "Excedidas en rango",
                p.records.reduce((sum, x) => sum + x.excess, 0),
                "ex-bad",
              ),
              h("span", "ex-chevron", "⌄"),
            ),
            div(
              "ixs-table-scroll",
              h(
                "table",
                "ixs-table",
                h(
                  "thead",
                  "",
                  h(
                    "tr",
                    "",
                    heading("Fecha", "fecha"),
                    heading("Inicio", "inicio"),
                    heading("Fin", "fin"),
                    [
                      "Task",
                      "Descripción",
                      "Tipo",
                      "Horas del registro",
                      "Excedidas",
                      "Acumulado",
                    ].map((x) => h("th", "", x)),
                  ),
                ),
                h(
                  "tbody",
                  "",
                  visible.map((x) =>
                    h(
                      "tr",
                      "",
                      td(dateText(x.fecha)),
                      td(x.inicio || "—"),
                      td(x.fin || "—"),
                      td(x.actividad || "Sin task"),
                      h("td", "ex-description", x.descripcion || "—"),
                      td(x.billable ? "Facturable" : "No facturable"),
                      td(num(x.duracion, 2)),
                      h("td", "ex-over", num(x.excess, 2)),
                      td(num(x.cumulative, 2)),
                    ),
                  ),
                ),
              ),
            ),
            h(
              "footer",
              "ex-pagination",
              h(
                "span",
                "",
                `Mostrando ${start + 1}–${Math.min(start + 8, records.length)} de ${records.length} registros`,
              ),
              el(
                "nav",
                { "aria-label": "Páginas de registros de " + p.name },
                button("←", () => actions.page(i, page - 1), "", {
                  disabled: page === 1,
                  "aria-label": "Página anterior",
                }),
                ...numbers.flatMap((n, j) => [
                  ...(j && n > numbers[j - 1] + 1 ? [h("span", "", "…")] : []),
                  button(
                    n,
                    () => actions.page(i, n),
                    n === page ? "active" : "",
                    { "aria-current": n === page ? "page" : null },
                  ),
                ]),
                button("→", () => actions.page(i, page + 1), "", {
                  disabled: page === pages,
                  "aria-label": "Página siguiente",
                }),
              ),
            ),
          );
        })
      : [empty("No hay registros excedidos en las fechas seleccionadas.")]),
  );
}

export function excessCsv(projectId, people) {
  const quote = (value) => {
    let text = String(value ?? "");
    if (/^[=+@-]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  };
  const rows = [
    [
      "Proyecto",
      "Recurso",
      "Rol",
      "Fecha",
      "Inicio",
      "Fin",
      "Task",
      "Descripción",
      "Tipo",
      "Horas registro",
      "Horas excedidas",
    ],
  ];
  people.forEach((p) =>
    p.records.forEach((x) =>
      rows.push([
        projectId,
        p.name,
        p.role,
        String(x.fecha || "")
          .split("-")
          .reverse()
          .join("/"),
        x.inicio,
        x.fin,
        x.actividad || "Sin task",
        x.descripcion,
        x.billable ? "Facturable" : "No facturable",
        x.duracion,
        Number(x.excess.toFixed(4)),
      ]),
    ),
  );
  return "\ufeff" + rows.map((row) => row.map(quote).join(",")).join("\r\n");
}
