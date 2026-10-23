import { apiGet } from "#app/data/api-client.js";
import { el } from "#app/lib/dom.js";

const node = (tag, props = {}, ...children) =>
  el(tag, props, ...children.flat(Infinity));
const cell = (value, cls = "") => el("td", { class: cls, text: value });
const badge = (value, bad) =>
  el("span", { class: "bd " + (bad ? "bad" : "ok"), text: value });
const link = (project, value) => el("a", { href: project.url, text: value });

function ixbRow(p) {
  const status = p.status
    ? el("span", {
        class: "st " + p.status_code,
        text:
          (p.status_code === "sus"
            ? "⏸"
            : p.status_code === "dep"
              ? "🚀"
              : p.status_code === "dev"
                ? "</>"
                : "⚲") +
          " " +
          p.status,
      })
    : "—";
  return node(
    "tr",
    {
      "data-manager": p.manager,
      "data-service": p.service,
      "data-start": p.start,
      "data-end": p.end,
    },
    cell(p.manager),
    node("td", {}, link(p, p.project_id)),
    node(
      "td",
      {},
      el("span", {
        class: "service-pill " + (p.service === "RaaS" ? "raas" : ""),
        text: p.service,
      }),
    ),
    node("td", {}, link(p, p.name)),
    node("td", {}, status),
    cell(p.start),
    cell(p.end),
    ["budget", "burn", "etc", "etc"].map((key) => cell(p.display[key], "n")),
    node(
      "td",
      { class: "c" },
      node(
        "div",
        { class: "advance " + (p.progress_bad ? "over" : "") },
        badge(p.display.progress + "%", p.progress_bad),
      ),
    ),
    p.stages.map((stage) => [
      cell(stage.total, "n"),
      cell(stage.closed, "n"),
      stage.alert
        ? node(
            "td",
            { class: "n" },
            el("span", { class: "pd", text: stage.pending }),
          )
        : cell(stage.pending, "n"),
    ]),
    cell(p.risks, "n"),
  );
}
export function renderIxbHistory(data) {
  if (data.error) return [el("p", { class: "note", text: data.error })];
  const heads = [
    ["Delivery Manager", ""],
    ["Project ID", ""],
    ["Service", ""],
    ["Nombre", ""],
    ["Estatus", ""],
    ["Start", ""],
    ["Finish", ""],
    ["Budget", "n"],
    ["Burn", "n"],
    ["ETC", "n"],
    ["Desv. Hrs", "n"],
    ["% Consumo", "c"],
  ];
  const first = node(
    "tr",
    {},
    heads.map(([text, cls]) => el("th", { rowspan: 2, class: cls, text })),
    ["Discovery", "Development", "Deployment", "General"].map((text) =>
      el("th", { class: "gh", colspan: 3, text }),
    ),
    el("th", { rowspan: 2, class: "n", text: "Riesgos" }),
  );
  first.querySelectorAll("th").forEach((th, i) => {
    if ([0, 1, 3, 4, 5, 7, 9, 11, 16].includes(i))
      th.classList.add("evtable-8b06b3");
  });
  const second = node(
    "tr",
    {},
    Array.from({ length: 4 }, () =>
      [
        ["🤖", "Total de Work Items"],
        ["✅", "Work Items cerrados"],
        ["⌛", "Work Items pendientes"],
      ].map(([text, title]) =>
        el("th", { class: "wi-icon", title, "aria-label": title, text }),
      ),
    ),
  );
  const body = data.projects.length
    ? data.projects.map(ixbRow)
    : [
        node(
          "tr",
          {},
          el("td", {
            colspan: 25,
            class: "vacio",
            text: "Todavía no hay proyectos IXB, RaaS o SaaS cerrados.",
          }),
        ),
      ];
  return [
    node(
      "div",
      { class: "tw" },
      node(
        "table",
        { class: "d w project-table", id: "eva-closed-table" },
        node("thead", {}, first, second),
        node("tbody", {}, body),
      ),
    ),
    node(
      "div",
      { class: "table-bottom" },
      el("span", { text: data.projects.length + " proyectos cerrados" }),
    ),
  ];
}

export function renderAerHistory(data) {
  if (data.error) return [el("p", { class: "note", text: data.error })];
  const rows = data.projects.map((p) =>
    node(
      "tr",
      {
        "data-closed-id": p.project_id,
        "data-budget": p.budget,
        ...(p.burn === null ? { "data-missing-burn": true } : {}),
      },
      cell(p.manager),
      node("td", {}, link(p, p.project_id)),
      cell(p.service),
      cell(p.name),
      node("td", {}, el("span", { class: "bd", text: p.closed_status })),
      cell(p.start),
      cell(p.end),
      cell(p.display.budget),
      node(
        "td",
        { "data-closed-field": "burn" },
        p.burn !== null ? badge(p.display.burn, p.burn > p.budget) : "Sin dato",
      ),
      node(
        "td",
        { "data-closed-field": "etc" },
        p.etc !== null ? badge(p.display.etc, p.etc < 0) : "Sin dato",
      ),
      node(
        "td",
        { "data-closed-field": "progress" },
        p.progress !== null
          ? badge(p.display.progress + "%", p.progress > 100)
          : "Sin dato",
      ),
    ),
  );
  if (!rows.length)
    rows.push(
      node(
        "tr",
        {},
        el("td", {
          colspan: 11,
          text: "Sin proyectos AER/T&M finalizados o cancelados en 2026 en MPB.",
        }),
      ),
    );
  return [
    node(
      "div",
      { class: "sc" },
      node(
        "table",
        {},
        node(
          "thead",
          {},
          node(
            "tr",
            {},
            [
              "Delivery Manager",
              "Project ID",
              "Service",
              "Nombre",
              "Estatus",
              "Start",
              "Finish",
              "Budget",
              "Burn",
              "ETC",
              "Avance",
            ].map((text) => el("th", { text })),
          ),
        ),
        node("tbody", {}, rows),
      ),
    ),
    el("p", {
      class: "note",
      text:
        data.projects.length +
        " proyectos finalizados o cancelados en 2026. Fuente: MPB.",
    }),
  ];
}

export function mountHistory({
  box,
  body,
  path,
  aer = false,
  afterLoad = () => {},
}) {
  let loaded = false,
    busy = false;
  async function load() {
    if (loaded || busy) return;
    busy = true;
    if (aer) body.textContent = "Cargando proyectos finalizados...";
    else
      body.replaceChildren(
        el("p", {
          class: "note",
          text: "Cargando proyectos cerrados… puede tardar unos segundos.",
        }),
      );
    try {
      const result = await apiGet(path, undefined, { timeout: 90000 });
      body.replaceChildren(
        ...(aer
          ? renderAerHistory(result.data)
          : renderIxbHistory(result.data)),
      );
      loaded = true;
      afterLoad(body);
    } catch (error) {
      const retry = el("button", {
        type: "button",
        class: aer ? null : "eva-btn",
        ...(aer ? {} : { id: "eva-closed-retry" }),
        text: "Reintentar",
        onclick: load,
      });
      body.replaceChildren(
        node(
          "p",
          { class: aer ? null : "note" },
          aer
            ? "No se pudo cargar el historico. "
            : "No se pudo cargar el histórico. ",
          retry,
        ),
      );
    } finally {
      busy = false;
    }
  }
  box.addEventListener("toggle", () => {
    if (box.open) load();
  });
}
