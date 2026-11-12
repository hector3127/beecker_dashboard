import {
  previousMonth,
  selectMonths,
  withComparison,
} from "./sections/period_summary.js";
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
} from "./sections/summary.js?v=20261111-range";

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
  for (const key of ["mes", "corte", "history_year", "anio"]) {
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
  const card = el(
    "div",
    { class: "card" },
    el("h2", {
      text: `Tendencia de cumplimiento en costo · ${filters.chart_year}`,
    }),
    el("div", {
      class: "hs",
      text: "Cumplimiento en costo (C) por DM y mes: proyectos con avance ≤ 100% sobre TP. Más alto es mejor. Usa el año del filtro superior y la selección global de DMs.",
    }),
  );
  if (!history.chart) {
    card.append(
      el("p", {
        class: "note",
        text: `No se pudo reconstruir el histórico. ${history.error || "Sin histórico disponible."}`,
      }),
    );
    return card;
  }
  const plot = el("div", {}, ...renderChart(history.chart));
  card.append(plot);
  return card;
}

/** @param {any} data */
function render(data) {
  const { history, picker } = data;
  const lastMonth =
    data.filters.history_year === Number(data.filters.month.slice(0, 4))
      ? Number(data.filters.month.slice(5))
      : 12;
  const params = new URLSearchParams(location.search);
  const first = Number(params.get("rango_desde"));
  const last = Number(params.get("rango_hasta"));
  const range =
    first >= 1 && last <= 12 && first <= last
      ? { start: first, end: last }
      : { start: Math.max(1, lastMonth - 2), end: lastMonth };
  data.range = range;
  const matrix = history.months
    ? selectMonths(history.months, range.start, range.end)
    : null;
  const summary = matrix
    ? withComparison(data.summary, data.previous, matrix)
    : data.summary;
  notice.replaceChildren(
    ...(history.notice
      ? [el("div", { class: "err", role: "status", text: history.notice })]
      : []),
  );
  const monthlyHistory = renderHistory({
    id: "kpi-month-history",
    title: `Histórico por mes · ${data.filters.history_year}`,
    hint: "Cada mes usa su última captura KPI guardada; T = % con desviación ≤ 0; C = % con avance ≤ 100%. Se muestran los meses del rango seleccionado; meses sin datos permanecen pendientes. El mes abierto (*) es provisional. Los meses sin captura permanecen pendientes; la automatización diaria se activará en Genesis.",
    matrix: matrix || { headers: [], rows: [], totals: [] },
    managerUrl,
    byMonth: true,
  });
  clearState(content);
  content.append(
    renderTabs(urls, picker.query),
    ...renderFilter(data),
    renderCards(summary),
    el("section", { class: "two" }, monthlyHistory, chartCard(data)),
  );
  if (!history.months) return;
  content.append(renderTable(summary, managerUrl));
  if (history.quarters) {
    content.append(
      renderHistory({
        id: "kpi-quarter-history",
        title: `Histórico por trimestre · ${data.filters.history_year}`,
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
    try {
      const previous = await apiGet("screens/kpis-dm/", {
        ...filters(),
        corte: "",
        mes: previousMonth(data.filters.month),
      });
      data.previous = previous.data.summary;
    } catch {
      data.previous = { available: false };
    }
    render(data);
  } catch (error) {
    showError(content, error, { onRetry: load });
  }
}

load();
