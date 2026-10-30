// @ts-check
// KPIs de Delivery Managers: corte, tabla por DM, grafica y historicos.
import { apiGet } from "#app/data/api-client.js";
import { el } from "#app/lib/dom.js";
import { clearState, showError, showLoading } from "#app/ui/states.js";
import { renderChart } from "./sections/chart.js?v=20261029-compliance";
import { renderHistory } from "./sections/history.js";
import {
  renderCards,
  renderFilter,
  renderTable,
  renderTabs,
} from "./sections/summary.js?v=20261029-month";

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const content = byId("kpis-content");
const notice = byId("kpis-notice");
const urls = {
  facturabilidad: content.dataset.facturabilidad || "",
  especialidad: content.dataset.especialidad || "",
  recurso: content.dataset.recurso || "",
  kpis: content.dataset.kpis || "",
  area: content.dataset.area || "",
};
const managerUrl = content.dataset.managerUrl || "";

/** Los filtros de periodo de la URL. */
function filters() {
  /** @type {Record<string, any>} */
  const out = {};
  const params = new URLSearchParams(location.search);
  for (const key of ["mes", "corte", "history_year", "chart_year", "anio"]) {
    const value = params.get(key);
    if (value) out[key] = value;
  }
  const managers = params.getAll("dm");
  if (managers.length) out.dm = managers;
  return out;
}

/** @param {any} data */
function chartCard(data) {
  const { history, filters } = data;
  const card = el("div", { class: "card" }, el("h2", { text: "Tendencia de cumplimiento en costo" }),
    el("div", { class: "hs", text: "Cumplimiento en costo (C) por DM y mes: proyectos con avance ≤ 100% sobre TP. Más alto es mejor. El año es independiente del mes consultado; se aplica la selección global de DMs." }));
  const year = el("select", { id: "kpi-chart-year", "aria-label": "Año de tendencia", onchange: (event) => {
    const url = new URL(location.href); url.searchParams.set("chart_year", event.target.value); location.assign(url.href);
  } }, ...filters.years.map(y => el("option", { value: y, selected: y === filters.chart_year, text: y })));
  const tools = el("div", { class: "kpi-local-filters" }, el("label", { for: "kpi-chart-year", text: "Año de tendencia" }), year);
  card.append(tools);
  if (!history.chart) { card.append(el("p", { class: "note", text: `No se pudo reconstruir el histórico. ${history.error || "Sin histórico disponible."}` })); return card; }
  const plot = el("div", {}, ...renderChart(history.chart));
  card.append(plot);
  return card;
}

function annualFilter(data) {
  const form = el("form", { method: "get", class: "kpi-local-filters" }, el("label", { for: "kpi-history-year", text: "Año de históricos" }),
    el("select", { id: "kpi-history-year", name: "history_year" }, ...data.filters.years.map(y => el("option", { value: y, selected: y === data.filters.history_year, text: y }))),
    el("button", { type: "submit", text: "Ver año" }));
  for (const key of ["mes", "chart_year"]) form.append(el("input", { type: "hidden", name: key, value: key === "mes" ? data.filters.month : data.filters[key] }));
  for (const name of new URLSearchParams(location.search).getAll("dm")) form.append(el("input", { type: "hidden", name: "dm", value: name }));
  return form;
}

/** @param {any} data */
function render(data) {
  const { summary, history, picker } = data;
  notice.replaceChildren(
    ...(history.notice
      ? [el("div", { class: "err", role: "status", text: history.notice })]
      : []),
  );
  clearState(content);
  content.append(
    renderTabs(urls, picker.query),
    ...renderFilter(data),
    renderCards(summary),
    el(
      "section",
      { class: "two" },
      renderTable(summary, managerUrl),
      chartCard(data),
    ),
  );
  content.append(annualFilter(data));
  if (!history.months) return;
  content.append(
    renderHistory({
      id: "kpi-month-history",
      title: "Histórico por mes",
      hint: "Cada mes usa su última captura KPI guardada; T = % con desviación ≤ 0; C = % con avance ≤ 100%. Los doce meses del año permanecen visibles; meses futuros sin datos. El mes abierto (*) es provisional. Los meses sin captura permanecen pendientes; la automatización diaria se activará en Genesis.",
      matrix: history.months,
      managerUrl,
      byMonth: true,
    }),
  );
  if (history.quarters) {
    content.append(
      renderHistory({
        id: "kpi-quarter-history",
        title: "Histórico por trimestre",
        hint: "Promedio de los meses de cada trimestre, como AVERAGE en Excel; no es el corte del último mes. TP es la carga promedio mensual (se presenta redondeada); T y C son promedios de los porcentajes mensuales T y C. * Trimestre parcial.",
        matrix: history.quarters,
        managerUrl,
        byMonth: false,
      }),
    );
  }
  content.append(
    el("p", {
      class: "note",
      text: `Fuente: tablas propias de KPIs de DMs. Última captura guardada: ${data.storage.latest_cut || "sin captura"}. La página no recalcula datos desde EVA, Azure ni Clockify. ${data.metrics.monthly_closes_enabled ? "Actualización diaria KPI habilitada." : "Actualización manual; programación diaria desactivada hasta Genesis."}`,
    }),
  );
}

async function load() {
  showLoading(content, "Consultando los indicadores…");
  try {
    const { data } = await apiGet("screens/kpis-dm/", filters());
    render(data);
    content.append(
      el("p", {
        class: "note",
        text: "Fórmulas: T = proyectos con desviación ≤ 0 / TP × 100; C = proyectos con avance ≤ 100% / TP del DM × 100. Los faltantes permanecen en TP y no se suman al numerador.",
      }),
    );
  } catch (error) {
    showError(content, error, { onRetry: load });
  }
}

load();
