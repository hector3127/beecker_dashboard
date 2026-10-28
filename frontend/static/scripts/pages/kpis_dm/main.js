// @ts-check
// KPIs de Delivery Managers: corte, tabla por DM, grafica y historicos.
import { apiGet } from "#app/data/api-client.js";
import { el } from "#app/lib/dom.js";
import { clearState, showError, showLoading } from "#app/ui/states.js";
import { renderChart } from "./sections/chart.js";
import { renderHistory } from "./sections/history.js";
import {
  renderCards,
  renderFilter,
  renderTable,
  renderTabs,
} from "./sections/summary.js";

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
  /** @type {Record<string, string>} */
  const out = {};
  const params = new URLSearchParams(location.search);
  for (const key of ["periodo", "anio", "trim", "mes"]) {
    const value = params.get(key);
    if (value) out[key] = value;
  }
  return out;
}

/** @param {any} data */
function chartCard(data) {
  const { period, history } = data;
  const card = el(
    "div",
    { class: "card" },
    el("h2", { text: "Cumplimiento por mes (C)" }),
  );
  card.append(
    el("div", {
      class: "hs",
      text: `C (% de proyectos dentro del presupuesto) por Delivery Manager · de enero a ${period.end_month}; el periodo elegido (${period.label}) va sombreado`,
    }),
  );
  if (history.months) card.append(...renderChart(history.chart));
  else {
    const failed = el("div", {
      text: `No se pudo reconstruir el histórico. ${history.error}`,
    });
    Object.assign(failed.style, {
      padding: "30px",
      textAlign: "center",
      color: "#4A4D86",
    });
    card.append(failed);
  }
  return card;
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
  if (!history.months) return;
  content.append(
    renderHistory({
      id: "kpi-month-history",
      title: "Histórico por mes",
      hint: "Cada mes: TP al último lunes–jueves; T = % con desviación ≤ 0; C = % con avance ≤ 100%. El mes actual (*) es provisional hasta el último lunes–jueves disponible.",
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
        hint: "Promedio de los meses de cada trimestre, como AVERAGE en Excel; no es el corte del último mes. TP es la carga promedio mensual (se presenta redondeada); T y C son promedios de los porcentajes mensuales de cumplimiento. * Trimestre parcial.",
        matrix: history.quarters,
        managerUrl,
        byMonth: false,
      }),
    );
  }
  content.append(
    el("p", {
      class: "note",
      text: "Fuentes: inventario abierto de EVA 1 desde Proyectos e Historico_Proyectos A:J, con horas facturables de Clockify hasta cada corte. Se incluyen suspendidos; se excluyen completados y cancelados al corte. No se usan estados actuales de Azure para reconstruir los meses. Los históricos se recalculan con la información disponible y pueden diferir de correos archivados.",
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
        text: "Fórmulas: T = proyectos con desviación ≤ 0 / TP × 100; C = proyectos con avance ≤ 100% / TP × 100. Los faltantes se muestran pendientes y no reducen TP.",
      }),
    );
  } catch (error) {
    showError(content, error, { onRetry: load });
  }
}

load();
