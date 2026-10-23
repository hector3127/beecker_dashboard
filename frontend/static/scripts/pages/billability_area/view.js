import { months } from "./model.js";
import { el, node, text, input, select, label, button, icon } from "./ui.js";
import { overview } from "./general.js";
import { selectedArea } from "./selected-area.js";
import { resourceDetail, percentResources } from "./resources.js";
import { hoursDetail } from "./hours.js";
import { kpis } from "./kpis.js";

const sections = [
  ["general", "layers", "General"],
  ["detail", "people", "Detalle recurso"],
  ["kpis", "target", "KPIs"],
  ["percent", "bars", "% Recurso"],
  ["hours", "clock", "Detalle HRS"],
];
const titles = {
  general: [
    "Facturabilidad por área",
    "Distribución mensual de horas reales, facturabilidad, capacidad y recursos por área.",
  ],
  detail: [
    "GSE · Detalle recurso",
    "Horas por persona, proyecto, banda y servicio.",
  ],
  kpis: [
    "GSE · KPIs operativos",
    "Facturabilidad, madurez y distribución por servicio.",
  ],
  percent: [
    "GSE · % Recurso",
    "Facturabilidad mensual por recurso y promedio del período.",
  ],
  hours: [
    "GSE · Detalle HRS",
    "Horas por recurso y mes; AER visible y TYM, IxB, SaaS y RaaS desplegables.",
  ],
};
export const byId = (id) => document.getElementById(id);

export function shell(state, actions) {
  const panel = el(
    "section",
    { id: "gse-panel" },
    node(
      "div",
      "gm-hero",
      node("span", "gm-icon", icon("bars")),
      node(
        "div",
        null,
        text("h2", "Facturabilidad por área"),
        text(
          "p",
          "Distribución mensual de horas reales, facturabilidad, capacidad y recursos por área.",
        ),
      ),
      node("div", "gm-brand"),
    ),
    node(
      "div",
      "gse-tools",
      label(
        "Año",
        input(
          {
            id: "gse-year",
            type: "number",
            min: 2000,
            max: 2100,
            value: state.year,
          },
          () => {},
        ),
      ),
      label(
        "Área",
        select([["", "Todas las áreas"]], "", actions.area, { id: "gse-area" }),
      ),
      label(
        "Fuente",
        select(
          [
            ["api", "API Clockify"],
            ["sheet", "Base Clockify en Sheets"],
          ],
          state.source,
          () => {},
          { id: "gse-source" },
        ),
      ),
      label(
        "Jornada diaria",
        input(
          { id: "gse-day", type: "number", value: state.day, min: 1, max: 24 },
          actions.day,
        ),
      ),
      button("Consultar año", () => actions.load(false), "ci-btn primary", {
        id: "gse-load",
      }),
      button("↻ Actualizar sin caché", () => actions.load(true), "ci-btn", {
        id: "gse-refresh",
        title: "Vuelve a leer el Sheet sin usar resultados guardados",
      }),
      button("↓ Exportar CSV", actions.csv, "ci-btn", { id: "gse-csv" }),
      label(
        "Mes para IDs",
        select([], 0, () => {}, { id: "gse-detail" }),
      ),
      button("Obtener IDs Clockify", actions.ids, "ci-btn", { id: "gse-ids" }),
      button(
        "Detalle recursos",
        () => actions.section("detail"),
        "ci-btn primary",
        { id: "gse-resource-detail" },
      ),
      button("KPIs", () => actions.section("kpis"), "ci-btn primary", {
        id: "gse-kpis",
      }),
    ),
    node(
      "details",
      null,
      text("summary", "Días festivos por mes (editables)"),
      node(
        "div",
        "gse-holidays",
        months.map((m, i) =>
          label(
            m + " ",
            input(
              {
                type: "number",
                min: 0,
                max: 31,
                "data-holiday": i,
                value: state.holidays[i],
              },
              (v) => actions.holiday(i, v),
            ),
          ),
        ),
      ),
    ),
    el("div", {
      class: "gse-note",
      id: "gse-status",
      text: "Selecciona la fuente y pulsa Consultar año.",
    }),
    el("div", { id: "gse-errors", role: "status" }),
    el("div", { class: "gse-scroll", id: "gse-matrix" }),
    text(
      "div",
      "Facturable se obtiene de la columna C (Tipo de Proyecto) de CatalagoProyectos. Solo Optimización, Agentes Autónomos, Continuos Improvement y Laboratorio usan la lista común de CatalagoProyectos, vinculada por ID_Proyecto. Primero busca el ID con el sufijo _S1, _S2 o _CR de Task. Si no existe, utiliza el ID puro. El catálogo no se filtra por mes; las horas de Clockify sí. Sin Asignación conserva la regla de Project/Task/Tags. Administrativas usa Administrative Activities. Administrativo Operaciones suma Inversión Operaciones e Inversión Comercial. Las categorías pueden solaparse. Recursos cuenta personas únicas con horas positivas en el mes. Capacidad mensual = horas diarias × personas × días laborables (lunes a viernes menos festivos). NA indica mes sin consultar o consulta fallida.",
      "gse-note",
    ),
    el("div", { id: "gse-section-content" }),
  );
  byId("gse-host").append(panel);
}

export function render(state, selection, model, actions, focus) {
  const previousControl = focus && byId(focus);
  const caret =
    focus === "gse-resource-search" && previousControl
      ? [previousControl.selectionStart, previousControl.selectionEnd]
      : null;
  const panel = byId("gse-panel");
  panel.classList.add("gse-modern");
  panel.classList.toggle("gse-selected-area", !!state.area);
  const selectArea = byId("gse-area");
  selectArea.replaceChildren(
    el("option", { value: "", text: "Todas las áreas" }),
    ...state.areaList.map((a) => el("option", { value: a, text: a })),
  );
  selectArea.value = state.area;
  const matrix = byId("gse-matrix");
  matrix.classList.add("gm-dashboard");
  matrix.replaceChildren(
    ...(state.area
      ? selectedArea(state, selection, model, actions)
      : overview(state, selection, model, actions)),
  );
  if (!state.area) {
    for (const [id, symbol, title] of [
      ["gse-refresh", "clock", "Actualizar sin caché"],
      ["gse-csv", "layers", "Exportar CSV"],
      ["gse-ids", "target", "Obtener IDs Clockify"],
      ["gse-load", "target", "Consultar año"],
      ["gse-resource-detail", "people", "Detalle recursos"],
    ])
      byId(id).replaceChildren(icon(symbol), " " + title);
  }
  const errors = Object.entries(state.data)
    .filter(([, r]) => !r.ok && !r.pending && !r.sinDatos)
    .map(([key, r]) =>
      text(
        "p",
        (state.area ? months[Number(key.slice(-2)) - 1] : key) + ": " + r.error,
        "gse-bad",
      ),
    );
  const warning = Object.values(state.data).find((r) => r.catalogoAviso);
  if (warning) {
    const p = text(
      "p",
      state.area
        ? "Catálogo común: " +
            warning.catalogoAviso +
            " Facturable y las cuatro categorías del catálogo aparecen como NA; las demás horas se calcularon."
        : warning.catalogoAviso,
      "gse-warn",
    );
    if (state.area) errors.unshift(p);
    else errors.push(p);
  }
  byId("gse-errors").replaceChildren(...errors);
  const detail = byId("gse-detail"),
    prev = detail.value;
  detail.replaceChildren(
    ...months.map((m, i) => el("option", { value: i, text: m })),
  );
  detail.value = prev || String(new Date().getMonth());
  const hero = panel.querySelector(".gm-hero");
  hero.querySelector("h2").textContent = titles[selection.section][0];
  hero.querySelector("p").textContent = titles[selection.section][1];
  hero.querySelector(".gm-brand").replaceChildren(
    el(
      "nav",
      { class: "gse-sections", "aria-label": "Apartados GSE" },
      ...sections.map(([id, symbol, title]) => {
        const b = button(
          "",
          () => actions.section(id),
          id === selection.section ? "active" : "",
        );
        b.append(icon(symbol), title);
        return b;
      }),
    ),
  );
  const host = byId("gse-section-content");
  for (const child of panel.children)
    if (child !== hero && child !== host)
      child.style.display = selection.section === "general" ? "" : "none";
  host.style.display = selection.section === "general" ? "none" : "";
  host.replaceChildren();
  if (selection.section === "detail")
    host.append(resourceDetail(state, selection, model, actions));
  if (selection.section === "kpis")
    host.append(kpis(state, selection, model, actions));
  if (selection.section === "percent")
    host.append(percentResources(state, selection, model, actions));
  if (selection.section === "hours")
    host.append(...hoursDetail(state, selection, model, actions));
  if (focus) {
    const control = byId(focus);
    if (control) {
      control.focus();
      if (typeof control.setSelectionRange === "function") {
        control.setSelectionRange(
          ...(caret || [control.value.length, control.value.length]),
        );
      }
    }
  }
}
