// @ts-check
// KPIs de Delivery Managers: pide el periodo de la URL a la API y dibuja el
// corte, la grafica de C y el historico mensual y trimestral.
import { apiGet } from '#app/data/api-client.js';
import { readParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { mountPeriodFilter } from '#app/ui/period-filter.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderChart } from './sections/chart.js';
import { renderHistory } from './sections/history.js';
import { renderSummary } from './sections/summary.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const root = byId('kpi-root');
const content = byId('kpi-content');
const dmUrl = /** @type {string} */ (root.dataset.dmUrl);
const PERIOD_KEYS = ['periodo', 'anio', 'trim', 'mes'];

const params = readParams();
const period = Object.fromEntries(PERIOD_KEYS.filter((k) => params.has(k)).map((k) => [k, /** @type {string} */ (params.get(k))]));

/** @param {string} query "?periodo=..." que conservan las pestanas hermanas. */
function mountTabs(query) {
  const tabs = [
    ['Facturabilidad', root.dataset.tabFacturabilidad],
    ['Facturabilidad por especialidad', root.dataset.tabEspecialidad],
    ['Facturabilidad por recurso', root.dataset.tabRecurso],
    ['KPIs de Delivery Managers', ''],
    ['Facturabilidad por área', root.dataset.tabArea],
  ];
  byId('kpi-tabs').replaceChildren(
    ...tabs.map(([text, href]) => (href === '' ? el('a', { class: 'on', href: query || '#', 'aria-current': 'page', text }) : el('a', { href: `${href}${query}`, text }))),
  );
}

/** @param {any} body */
function render(body) {
  const { data } = body;
  const { summary, history, cut } = data;
  clearState(content);
  mountPeriodFilter(byId('kpi-period'), data.picker);
  mountTabs(data.picker.query);
  byId('kpi-cut').textContent = `${cut.current ? `Corte actual (${cut.label}).` : `Corte al ${cut.label}, reconstruido con las horas de Clockify hasta esa fecha.`} Los meses se reconstruyen por fecha; los trimestres promedian los cortes mensuales.`;
  const errors = byId('kpi-error');
  errors.replaceChildren(...(history.notice ? [el('div', { class: 'err', role: 'status', text: history.notice })] : []));
  renderSummary(content, summary, dmUrl);
  // La tabla por DM y la grafica van lado a lado.
  const two = el('div', { class: 'kpi-two' }, /** @type {Element} */ (content.lastElementChild));
  content.append(two);

  const chart = el('div', { class: 'card' });
  if (history.chart && history.months) {
    chart.append(el('h2', { text: 'Consumo por mes (C)' }), el('div', { class: 'hs', text: `C (avance promedio) por Delivery Manager · de enero a ${data.period.end_month}; el periodo elegido (${data.period.label}) va sombreado` }));
    renderChart(chart, history.chart);
  } else {
    chart.append(el('h2', { text: 'Consumo por mes (C)' }), el('p', { class: 'na', text: `No se pudo reconstruir el histórico. ${history.error}` }));
  }
  two.append(chart);

  if (history.months) {
    renderHistory(content, {
      id: 'kpi-month-history',
      title: 'Histórico por mes',
      hint: 'Cada mes muestra TP (proyectos), T (desviación en días) y C (consumo de horas sobre presupuesto). El mes en curso (*) llega hasta hoy.',
      matrix: history.months,
      dmUrl,
      rounded: false,
      monthly: true,
    });
    renderHistory(content, {
      id: 'kpi-quarter-history',
      title: 'Histórico por trimestre',
      hint: 'Promedio de los meses de cada trimestre, como AVERAGE en Excel; no es el corte del último mes. TP es la carga promedio mensual (se presenta redondeada); T sigue en días y C en porcentaje de consumo. * Trimestre parcial.',
      matrix: history.quarters,
      dmUrl,
      rounded: true,
      monthly: false,
    });
    content.append(
      el('p', {
        class: 'note',
        text: 'Fuentes: AER y T&M de MPB (ID, servicio, inicio, fin, estatus, Delivery Manager y HORAS); otros servicios de Historico_Proyectos A:I (Delivery Manager, cliente, ID, servicio, nombre, etapas y fechas desde Discovery OP hasta su cierre), con Budget (Hrs) de J por ID de proyecto. Cada corte usa las horas facturables de Clockify hasta esa fecha. No se consulta Proyectos ni el bloque derecho del histórico. Los contratos MPB se evalúan por sus fechas y estatus disponibles; los riesgos se toman del corte actual. C queda sin dato si falta un presupuesto válido.',
      }),
    );
  }
}

async function load() {
  showLoading(content, 'Consultando el periodo…');
  try {
    render(await apiGet('screens/kpis-dm/', period));
  } catch (error) {
    showError(content, error, { onRetry: load });
  }
}

load();
