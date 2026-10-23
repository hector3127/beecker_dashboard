// @ts-check
// KPIs de Delivery Managers: corte, tabla por DM, grafica y historicos.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderChart } from './sections/chart.js';
import { renderHistory } from './sections/history.js';
import { renderCards, renderFilter, renderTable, renderTabs } from './sections/summary.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const content = byId('kpis-content');
const notice = byId('kpis-notice');
const urls = {
  facturabilidad: content.dataset.facturabilidad || '',
  especialidad: content.dataset.especialidad || '',
  recurso: content.dataset.recurso || '',
  kpis: content.dataset.kpis || '',
  area: content.dataset.area || '',
};
const managerUrl = content.dataset.managerUrl || '';

/** Los filtros de periodo de la URL. */
function filters() {
  /** @type {Record<string, string>} */
  const out = {};
  const params = new URLSearchParams(location.search);
  for (const key of ['periodo', 'anio', 'trim', 'mes']) {
    const value = params.get(key);
    if (value) out[key] = value;
  }
  return out;
}

/** @param {any} data */
function chartCard(data) {
  const { period, history } = data;
  const card = el('div', { class: 'card' }, el('h2', { text: 'Consumo por mes (C)' }));
  card.append(el('div', { class: 'hs', text: `C (avance promedio) por Delivery Manager · de enero a ${period.end_month}; el periodo elegido (${period.label}) va sombreado` }));
  if (history.months) card.append(...renderChart(history.chart));
  else {
    const failed = el('div', { text: `No se pudo reconstruir el histórico. ${history.error}` });
    Object.assign(failed.style, { padding: '30px', textAlign: 'center', color: '#4A4D86' });
    card.append(failed);
  }
  return card;
}

/** @param {any} data */
function render(data) {
  const { summary, history, picker } = data;
  notice.replaceChildren(...(history.notice ? [el('div', { class: 'err', role: 'status', text: history.notice })] : []));
  clearState(content);
  content.append(renderTabs(urls, picker.query), ...renderFilter(data), renderCards(summary), el('section', { class: 'two' }, renderTable(summary, managerUrl), chartCard(data)));
  if (!history.months) return;
  content.append(
    renderHistory({
      id: 'kpi-month-history',
      title: 'Histórico por mes',
      hint: 'Cada mes muestra TP (proyectos), T (desviación en días) y C (consumo de horas sobre presupuesto). El mes en curso (*) llega hasta hoy.',
      matrix: history.months,
      managerUrl,
      byMonth: true,
    }),
  );
  if (history.quarters) {
    content.append(
      renderHistory({
        id: 'kpi-quarter-history',
        title: 'Histórico por trimestre',
        hint: 'Promedio de los meses de cada trimestre, como AVERAGE en Excel; no es el corte del último mes. TP es la carga promedio mensual (se presenta redondeada); T sigue en días y C en porcentaje de consumo. * Trimestre parcial.',
        matrix: history.quarters,
        managerUrl,
        byMonth: false,
      }),
    );
  }
  content.append(
    el('p', {
      class: 'note',
      text: 'Fuentes: AER y T&M de MPB (ID, servicio, inicio, fin, estatus, Delivery Manager y HORAS); otros servicios de Historico_Proyectos A:I (Delivery Manager, cliente, ID, servicio, nombre, etapas y fechas desde Discovery OP hasta su cierre), con Budget (Hrs) de J por ID de proyecto. Cada corte usa las horas facturables de Clockify hasta esa fecha. No se consulta Proyectos ni el bloque derecho del histórico. Los contratos MPB se evalúan por sus fechas y estatus disponibles; los riesgos se toman del corte actual. C queda sin dato si falta un presupuesto válido.',
    }),
  );
}

async function load() {
  showLoading(content, 'Consultando los indicadores…');
  try {
    const { data } = await apiGet('screens/kpis-dm/', filters());
    render(data);
    content.append(el('p', { class: 'note', text: 'Fórmulas de esta reconstrucción: T es desviación promedio en días y C es consumo promedio del presupuesto de horas. No deben interpretarse como los porcentajes de cumplimiento T/C del reporte mensual de Excel.' }));
  } catch (error) {
    showError(content, error, { onRetry: load });
  }
}

load();
