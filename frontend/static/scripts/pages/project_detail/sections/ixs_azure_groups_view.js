import { el } from "#app/lib/dom.js";
import { h, div } from "./ixs_executive_view.js";
import { statusClass } from "./ixs_planning_azure.js";
import { iterationStage } from "./ixs_azure_groups_model.js";

const chip = (n, color = "") =>
  h("span", `ixs-az84-count ${color}`, Number(n) || 0);
const counts = (row) => [
  chip(row.closed, "green"),
  chip(row.active),
  chip(row.proposed, "blue"),
  chip(row.cancelled, "pink"),
  chip(row.other, "orange"),
];
const heads = (labels) =>
  h(
    "thead",
    "",
    h(
      "tr",
      "",
      labels.map((x) => h("th", "", x)),
    ),
  );
const action = (label, callback, type) =>
  el("button", { type, class: "ixs-az84-action", onclick: callback }, label);

export function groupViews(groups, state, handlers) {
  if (!(state.allItems || []).length)
    return {
      people: [
        div(
          "ixs-azure-empty",
          "No hay Work Items registrados en este proyecto.",
        ),
      ],
      stages: [
        div(
          "ixs-azure-empty",
          "No hay Work Items registrados en este proyecto.",
        ),
      ],
    };
  const cards = groups.people.map((person, i) => {
    const rows = person.iteraciones.map((row, j) =>
      h(
        "tr",
        "",
        h("td", "", "↳ " + row.etapa),
        counts(row).map((c) => h("td", "", c)),
        h("td", "", h("b", "", row.items.length)),
        h(
          "td",
          "",
          action("Ver ítems", () => handlers.iteration(i, j), "button"),
        ),
      ),
    );
    return el(
      "details",
      {
        class: "ixs-az85-person",
        dataset: { ixsPerson: person.persona.toLocaleLowerCase("es") },
      },
      h(
        "summary",
        "",
        el("span", { class: "ixs-az85-chev", "aria-hidden": "true" }, "▶"),
        h(
          "span",
          "ixs-az85-person-name",
          person.persona,
          h("small", "", `${person.iteraciones.length} iteración(es)`),
        ),
        counts(person),
        h("span", "ixs-az85-total", person.total),
        action(
          "Ver ítems",
          (event) => {
            event.preventDefault();
            event.stopPropagation();
            handlers.person(i);
          },
          "button",
        ),
      ),
      div(
        "ixs-az85-sub-wrap",
        h(
          "table",
          "ixs-az85-sub-table",
          heads([
            "Iteración",
            "Closed",
            "Active",
            "Proposed",
            "Cancel.",
            "Otros",
            "Total",
            "Acción",
          ]),
          h("tbody", "", rows),
        ),
      ),
    );
  });
  const search = el("input", {
    type: "search",
    "aria-label": "Buscar persona o iteración",
    placeholder: "Buscar persona o iteración…",
    oninput: (event) => handlers.filter(event.target.value, cards),
  });
  const stageRows = groups.stages.map((row, i) =>
    h(
      "tr",
      "",
      h("td", "", h("b", "", row.etapa)),
      h("td", "num", chip(row.active)),
      h("td", "num", chip(row.proposed, "blue")),
      h("td", "num", chip(row.blocked, "pink")),
      h("td", "num", chip(row.other, "orange")),
      h("td", "num", row.items.length),
      h(
        "td",
        "",
        action("Ver abiertos", () => handlers.stage(i)),
      ),
    ),
  );
  return {
    people: [
      div(
        "ixs-az85-person-tools",
        search,
        h(
          "small",
          "",
          `${groups.people.length} personas · ${state.allItems.length} ítems`,
        ),
      ),
      div(
        "ixs-az85-people-scroll",
        div(
          "ixs-az85-people",
          div(
            "ixs-az85-columns",
            [
              "",
              "Persona",
              "Closed",
              "Active",
              "Proposed",
              "Cancel.",
              "Otros",
              "Total",
              "Acción",
            ].map((x) => h("span", "", x)),
          ),
          cards,
        ),
      ),
      div(
        "ixs-az84-notice",
        state.notice ||
          "Haz clic en una persona para ver sus iteraciones. “Ver ítems” abre el detalle de ese grupo.",
      ),
    ],
    stages: [
      div(
        "ixs-az84-tablewrap",
        h(
          "table",
          "ixs-az84-table",
          heads([
            "Iteración / etapa",
            "Active",
            "Proposed",
            "Blocked",
            "Otros abiertos",
            "Total abiertos",
            "Acción",
          ]),
          h("tbody", "", stageRows),
        ),
      ),
      div(
        "ixs-az84-notice",
        "Abiertos = estados distintos de Not applicable, Cancelled, Closed, Rejected, Completed e Inactive.",
      ),
    ],
  };
}

export function groupDrawer(projectId, items, title, subtitle, close) {
  const wrap = el("div", {
    id: "ixs-az84-drawer-wrap",
    class: "ixs-az84-drawer-wrap",
    onclick: (event) => {
      if (event.target === wrap) close();
    },
  });
  wrap.append(
    el(
      "aside",
      {
        class: "ixs-az84-drawer",
        role: "dialog",
        "aria-modal": "true",
        "aria-label": title,
      },
      div(
        "ixs-az84-drawer-head",
        h(
          "div",
          "",
          h("h3", "", title),
          h(
            "small",
            "",
            `${projectId} · ${subtitle}`,
            h("br", ""),
            `${items.length} Work Item(s). Abre cada número en Azure DevOps.`,
          ),
        ),
        el(
          "button",
          { class: "ixs-az84-close", onclick: close, "aria-label": "Cerrar" },
          "✕",
        ),
      ),
      div(
        "ixs-az84-drawer-list",
        items.length
          ? items.map((item) =>
              h(
                "article",
                "ixs-az84-drawer-item",
                div(
                  "top",
                  el(
                    "a",
                    {
                      href: item.url || "#",
                      target: "_blank",
                      rel: "noopener noreferrer",
                    },
                    "#" + (item.id ?? ""),
                  ),
                  h(
                    "span",
                    `ixs-azure-badge ${statusClass(item.estado)}`,
                    item.estado || "—",
                  ),
                ),
                h("p", "", item.titulo || "Sin título"),
                h(
                  "small",
                  "",
                  `${item.asignadoA || "Sin asignar"} · ${iterationStage(item.iterationPath)}`,
                ),
              ),
            )
          : h("p", "", "Sin Work Items."),
      ),
    ),
  );
  return wrap;
}
