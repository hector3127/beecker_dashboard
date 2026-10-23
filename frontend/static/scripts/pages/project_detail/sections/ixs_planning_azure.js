import { el } from "#app/lib/dom.js";
import { h, div } from "./ixs_executive_view.js";
import { icon } from "./ixs_icons.js";

function requirement(title) {
  const text = String(title || "").trim();
  return (
    (text.match(/[A-Z]{2,}\.[0-9]{3}(?:\.[0-9]{3})+/i) ||
      text.match(/[A-Z]{2,}\.[0-9]{3}(?:_[A-Z0-9]+)?/i) ||
      [])[0] || "—"
  );
}
function titleOnly(title) {
  const text = String(title || "").trim(),
    req = requirement(text);
  return req === "—"
    ? text
    : text
        .replace(req, "")
        .replace(/^[-–—:|\s]+/, "")
        .trim() || text;
}
export function statusClass(state) {
  const value = String(state || "").toLowerCase();
  if (
    [
      "not applicable",
      "cancelled",
      "closed",
      "rejected",
      "completed",
      "inactive",
    ].includes(value)
  )
    return "closed";
  if (
    value.includes("block") ||
    value.includes("escalad") ||
    value.includes("risk")
  )
    return "blocked";
  if (value.includes("proposed") || value.includes("nuevo")) return "proposed";
  if (
    ["active", "activ", "progress", "resolved"].some((x) => value.includes(x))
  )
    return "active";
  return "other";
}
const colors = {
  closed: "#1ca66d",
  proposed: "#4b8ef1",
  blocked: "#e53051",
  active: "#7e4bf0",
  other: "#948fb0",
};

export function planningAzureSection(state, actions) {
  const box = el("div", { id: "ixs-azure-table", class: "ixs-azure-empty" });
  const selects = [];
  const select = (key, label, sourceKey) => {
    const values =
      state.cargando || state.error
        ? []
        : Array.from(
            new Set(
              (state.items || [])
                .map((x) => String((x && x[sourceKey]) || "").trim())
                .filter(Boolean),
            ),
          ).sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" }));
    const node = el(
      "select",
      {
        id: "ixs-azure-filter-" + key,
        class: "ixs-azure-select",
        onchange: filter,
      },
      el("option", { value: "" }, label),
      ...values.map((x) => el("option", { value: x }, x)),
    );
    selects.push(node);
    return node;
  };
  const search = el("input", {
    id: "ixs-azure-filter-search",
    class: "ixs-azure-search",
    type: "search",
    placeholder: "Buscar work item…",
    oninput: filter,
  });
  const filters = div(
    "ixs-azure-filters",
    select("estado", "Estado", "estado"),
    select("asignado", "Asignado", "asignadoA"),
    select("tipo", "Tipo", "tipo"),
    search,
  );
  function filter() {
    if (state.cargando || state.error) {
      box.textContent = state.cargando
        ? "Consultando Azure DevOps…"
        : state.error;
      return;
    }
    const [status, person, type] = selects.map((x) => x.value),
      query = String(search.value || "")
        .trim()
        .toLowerCase();
    const staleMap = {};
    state.items.forEach((x) => {
      staleMap[String(x.id)] = x.tipo || "";
    });
    const rows = state.items.filter((x) => {
      const kind = String(x.tipo || staleMap[String(x.id)] || "");
      if (
        (status && String(x.estado || "") !== status) ||
        (person && String(x.asignadoA || "") !== person) ||
        (type && kind !== type)
      )
        return false;
      return (
        !query ||
        [
          x.id,
          requirement(x.titulo),
          titleOnly(x.titulo),
          x.asignadoA,
          x.estado,
          kind,
          x.demo,
        ]
          .join(" ")
          .toLowerCase()
          .includes(query)
      );
    });
    if (!rows.length) {
      box.replaceChildren(
        div(
          "ixs-azure-empty",
          "No hay work items que coincidan con los filtros seleccionados.",
        ),
      );
      return;
    }
    const td = (value, cls = "") => h("td", cls, value);
    const input = (x, field, value, props = {}, convert = (v) => v) =>
      el("input", {
        value,
        ...props,
        onchange: (event) =>
          actions.update(
            Number(x.id) || 0,
            field,
            convert(
              event.target.type === "checkbox"
                ? event.target.checked
                : event.target.value,
            ),
          ),
      });
    box.replaceChildren(
      div(
        "ixs-azure-tablewrap",
        h(
          "table",
          "ixs-azure-table",
          h(
            "thead",
            "",
            h(
              "tr",
              "",
              [
                "#",
                "Req.",
                "Asignado",
                "Estado",
                "Dev construido",
                "QA",
                "Fecha límite Dev",
                "Demo",
                "% avance total",
                "Comentarios",
              ].map((x) => h("th", "", x)),
            ),
          ),
          h(
            "tbody",
            "",
            rows.map((x) => {
              const dot = h("span", "state-dot");
              dot.style.background = colors[statusClass(x.estado)];
              const percent = Math.max(
                  0,
                  Math.min(100, Number(x.avanceTotal) || 0),
                ),
                bar = h("i", "");
              bar.style.width = percent + "%";
              return el(
                "tr",
                { id: "wi-row-" + x.id },
                td(
                  div(
                    "req",
                    dot,
                    el(
                      "a",
                      { href: x.url || "#", target: "_top" },
                      "#" + (x.id ?? ""),
                    ),
                  ),
                ),
                td(
                  div(
                    "title",
                    h("b", "", requirement(x.titulo)),
                    h("br", ""),
                    titleOnly(x.titulo),
                  ),
                ),
                td(x.asignadoA || "—", "assignee"),
                td(
                  h(
                    "span",
                    `ixs-azure-badge ${statusClass(x.estado)}`,
                    x.estado || "—",
                  ),
                ),
                h(
                  "td",
                  "",
                  input(
                    x,
                    "devConstruido",
                    Number(x.devConstruidoPct) || 0,
                    {
                      class: "ixs-azure-mini-input",
                      type: "number",
                      min: 0,
                      max: 100,
                    },
                    Number,
                  ),
                  " %",
                ),
                h(
                  "td",
                  "ixs-plan-qa-cell",
                  input(x, "qa", undefined, {
                    class: "ixs-plan-qa-input",
                    type: "checkbox",
                    checked: !!x.qaListo,
                  }),
                ),
                td(
                  input(
                    x,
                    "fechaLimiteDev",
                    x.fechaLimiteDev
                      ? String(x.fechaLimiteDev).slice(0, 10)
                      : "",
                    { class: "ixs-azure-date-input", type: "date" },
                  ),
                ),
                td(
                  input(x, "demo", x.demo || "", {
                    class: "ixs-azure-text-input",
                    type: "text",
                  }),
                ),
                el(
                  "td",
                  { id: "wi-avance-" + x.id },
                  div(
                    "ixs-azure-progress",
                    div("track", bar),
                    h("b", "", percent + "%"),
                  ),
                ),
                h(
                  "td",
                  "",
                  div(
                    "ixs-azure-comment",
                    el("input", {
                      type: "text",
                      id: "wi-comentario-" + x.id,
                      placeholder: "Escribe un comentario...",
                    }),
                    el(
                      "button",
                      {
                        class: "ixs-btn ixs-plan-comment-send",
                        onclick: () => actions.comment(Number(x.id) || 0),
                      },
                      "Enviar",
                    ),
                  ),
                  el("div", {
                    class: "ixs-azure-comment-status",
                    id: "wi-comentario-status-" + x.id,
                  }),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
  filter();
  return h(
    "section",
    "ixs-card ixs-azure-wi-card ixs-plan-table",
    el(
      "details",
      { class: "ixs-azure-wi-collapse", open: true },
      h(
        "summary",
        "ixs-azure-wi-summary",
        h(
          "h3",
          "",
          icon("layers"),
          " Work Items — Azure DevOps (To Be / Change Request)",
        ),
        h(
          "span",
          "ixs-azure-wi-toggle",
          h("span", "show", "Mostrar tabla"),
          h("span", "hide", "Ocultar tabla"),
          h("span", "arrow", "▾"),
        ),
      ),
      div("ixs-azure-wi-content", filters, box),
    ),
  );
}
