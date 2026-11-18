// @ts-check
// Cifras de Financiera, Operaciones y Comercial, con el corte ya preparado.
// Un dato que aun no se prepara muestra «Cargando dato…»; uno que llego vacio
// dice «Pendiente», nunca cero.
import { costCoverage, verifiedCostBlockers } from './financial_model.js';
import { renderCardVisuals } from './card_visuals.js';
import { el } from '#app/lib/dom.js';
import { formatCompact } from '#app/lib/format.js';
import { mountMonthlyChart } from '#app/lib/monthly-chart.js';
import { showPendingDialog } from '#app/ui/pending-dialog.js';

const PENDING = 'Pendiente';
/** @param {number | string | null | undefined} n */
const whole = (n) => (n === null || n === undefined ? PENDING : Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 }));
/** @param {number | string | null | undefined} n */
const pct = (n) => (n === null || n === undefined ? PENDING : `${whole(n)}%`);
/** @param {string} id */
const node = (id) => document.getElementById(id);

/**
 * @typedef {object} Model
 * @property {any} revenue
 * @property {any} costs
 * @property {any} operations Cifras de operaciones (vacio si no hay).
 * @property {any} commercial
 * @property {any} monthly
 * @property {string | null} loadedAt
 */

/** Ids de las cifras que aun no llegan: se muestran como «Cargando dato…». @param {Model} model */
export function loadingIds(model) {
  const { revenue, costs, operations: ops, commercial } = model;
  return new Set([
    ...(!revenue ? ['executive-revenue', 'executive-collections'] : []),
    ...(!costs ? ['executive-margin'] : []),
    ...(ops.projects === null || ops.projects === undefined ? ['executive-ops-etc', 'executive-ops-advance', 'executive-ops-facturability', 'executive-ops-investment'] : []),
    ...(!commercial ? ['commercial-won', 'commercial-delivery', 'commercial-open'] : []),
    ...(!model.monthly ? ['monthly-profit-state'] : []),
  ]);
}

/** Quita el esqueleto de lo que sigue sin llegar. @param {Set<string>} loading */
export function finishLoading(loading) {
  for (const id of loading) {
    const target = node(id);
    if (id === 'monthly-profit-state' && target) {
      target.textContent = 'No disponible';
      const chart = node('monthly-profit-chart');
      if (chart) chart.textContent = 'No se pudo preparar la rentabilidad mensual. Intenta consultar el periodo de nuevo.';
    }
    if (target?.classList.contains('metric-loading')) {
      target.classList.remove('metric-loading');
      target.removeAttribute('aria-busy');
      target.removeAttribute('aria-label');
      target.textContent = 'No disponible';
    }
  }
}

/** @param {Set<string>} loading */
function setter(loading) {
  return (/** @type {string} */ id, /** @type {string} */ value) => {
    const target = node(id);
    if (!target) return;
    if (value === PENDING && loading.has(id)) {
      target.classList.add('metric-loading');
      target.setAttribute('aria-label', 'Cargando dato');
      target.setAttribute('aria-busy', 'true');
      target.replaceChildren(
        el('span', { class: 'metric-skeleton', 'aria-hidden': 'true' }),
        el('span', { class: 'metric-spinner', 'aria-hidden': 'true' }),
        el('span', { class: 'metric-loading-label', text: 'Cargando dato…' }),
      );
    } else {
      target.classList.remove('metric-loading');
      target.removeAttribute('aria-busy');
      target.removeAttribute('aria-label');
      target.textContent = value;
    }
  };
}

/** @param {Model} model @param {(id: string, value: string) => void} set */
function financial(model, set) {
  const { revenue = {}, costs = {} } = { revenue: model.revenue || {}, costs: model.costs || {} };
  set('executive-revenue', formatCompact(revenue.invoiced));
  set('executive-revenue-source', 'Importe de los registros facturados o cobrados del periodo, incluidos los de factoraje. Los ingresos confirmados se muestran por separado como ingresos contratados.');
  set('executive-collections', pct(revenue.collections_percent));
  set('executive-collected', formatCompact(revenue.collected));
  set('executive-contracted', formatCompact(revenue.total));
  set('executive-collections-note', 'Importe cobrado, incluido factoraje, como porcentaje de la facturación del mismo periodo y corte.');
  const income = Number(revenue.invoiced);
  const hasInvoice = revenue.invoiced !== null && revenue.invoiced !== undefined;
  const hasCosts = costs.cost !== null && costs.cost !== undefined && (costs.complete || (costs.projects || []).some((/** @type {any} */ p) => p.cost !== null && p.cost !== undefined) || Number(costs.deduplicated_entries) > 0);
  set('executive-gross-profit', hasCosts && hasInvoice ? formatCompact(income - Number(costs.cost)) + (costs.complete ? '' : '*') : PENDING);
  set('executive-margin', hasCosts && hasInvoice && income > 0 ? pct(((income - Number(costs.cost)) / income) * 100) + (costs.complete ? '' : '*') : PENDING);
  set('executive-margin-note', hasCosts ? (costs.complete ? 'Costos completos del periodo' : `* Parcial con costos disponibles: ${formatCompact(costs.cost)}.`) : 'Sin costos consultados para calcular el margen');
  const coverage = costCoverage(costs.projects || []);
  set('executive-cost-coverage', costs.projects ? `${coverage.complete} completos · ${coverage.partial} parciales · ${coverage.missing} sin costo disponible · ${coverage.total} proyectos incluidos${coverage.future ? ` · ${coverage.future} futuros fuera del cálculo de costos` : ''}` : PENDING);
  const blockers = verifiedCostBlockers(costs.projects || [], model.loadedAt);
  const button = /** @type {HTMLButtonElement | null} */ (node('executive-cost-blockers'));
  if (button) {
    button.hidden = !blockers.length;
    button.textContent = blockers.length
      ? `${blockers.length} ${blockers.length === 1 ? 'proyecto con costos' : 'proyectos con costos'} por revisar`
      : '';
    button.onclick = () =>
      showPendingDialog({
        title: 'Proyectos con costos por revisar',
        description: 'El margen es parcial mientras falten vínculos, fechas o tarifas. Los costos disponibles ya están incluidos en el cálculo.',
        columns: ['Proyecto', 'Costo disponible', 'Qué falta revisar'],
        rows: blockers.map((/** @type {any} */ p) => [p.id, formatCompact(p.cost), p.error || (p.cost === null || p.cost === undefined ? 'Costo no disponible; revisar la consulta del proyecto.' : `Falta banda o tarifa${p.missing_people?.length ? `: ${p.missing_people.join(', ')}` : ''}`)]),
        trigger: button,
      });
  }
}

/** @param {Model} model @param {(id: string, value: string) => void} set */
function operations(model, set) {
  const ops = model.operations;
  const known = ops.projects !== null && ops.projects !== undefined;
  const partial = ops.partial !== false;
  const some = (/** @type {unknown} */ v) => v !== null && v !== undefined;
  set('executive-ops-cut', known ? (partial ? 'Corte parcial' : 'Corte completo') : 'Consultando');
  set('executive-ops-etc', some(ops.capacity_consumed_hours) ? `${whole(ops.capacity_consumed_hours)} h${ops.capacity_partial ? '*' : ''}` : PENDING);
  set('executive-ops-advance', some(ops.advance) ? pct(ops.advance) + (ops.capacity_partial ? '*' : '') : PENDING);
  set('executive-ops-fte', ops.capacity_base > 0 ? `${whole(ops.capacity_base)} h de capacidad` : 'Capacidad pendiente');
  set('executive-ops-facturability', some(ops.facturability) ? `${Number(ops.facturability).toLocaleString('en-US', { maximumFractionDigits: 0 })}%${ops.facturability_partial ? '*' : ''}` : PENDING);
  set('executive-ops-facturability-month', ops.facturability_period ? (ops.facturability_partial ? 'Parcial · ' : '') + ops.facturability_period : '');
  set('executive-ops-investment', some(ops.investment_operational) ? `${whole(ops.investment_operational)} h` : PENDING);
  /** @type {Map<string, string[]>} */
  const pending = new Map();
  for (const id of ops.missing_budget_ids || []) pending.set(id, ['Sin presupuesto']);
  for (const id of ops.pending_ids || []) pending.set(id, [...(pending.get(id) || []), 'Consumo pendiente']);
  const button = /** @type {HTMLButtonElement | null} */ (node('executive-ops-status'));
  if (button) {
    const missing = (ops.missing_budget_ids || []).length;
    const noUse = (ops.pending_ids || []).length;
    button.textContent = !known ? 'Preparando corte…' : pending.size ? (missing ? `${whole(missing)} sin presupuesto${noUse ? ` · ${whole(noUse)} sin consumo` : ''}` : `${whole(noUse)} sin consumo`) : partial ? 'Corte parcial' : 'Corte completo';
    button.hidden = !pending.size;
    button.disabled = !pending.size;
    button.onclick = () => {
      if (!pending.size) return;
      showPendingDialog({
        title: 'Pendientes de Operaciones',
        description: 'Estos proyectos necesitan presupuesto o consumo para completar el corte operativo.',
        columns: ['Proyecto', 'Qué falta revisar'],
        rows: [...pending].map(([id, reasons]) => [id, reasons.join(' · ')]),
        trigger: button,
      });
    };
  }
  set('executive-ops-note', 'Las horas de inversión operativa corresponden a los registros del periodo seleccionado. Los indicadores se muestran como parciales cuando falta cobertura.');
}

/** @param {Model} model @param {(id: string, value: string) => void} set */
function commercial(model, set) {
  const data = model.commercial || {};
  set('commercial-won', formatCompact(data.won));
  set('commercial-won-note', data.won_count === null || data.won_count === undefined ? 'Pendiente de corte' : `${whole(data.won_count)} ventas ganadas · booking`);
  set('commercial-delivery', formatCompact(data.delivery));
  set('commercial-delivery-note', data.delivery_note || 'Pendiente de corte');
  const delivery = node('commercial-delivery');
  if (delivery) delivery.title = data.delivery_note || 'Ingresos confirmados futuros según la fecha registrada en Finanzas';
  set('commercial-open', formatCompact(data.open));
  set('commercial-open-note', data.open_note || 'Pendiente de corte');
  const open = node('commercial-open');
  if (open) open.title = data.open_note || 'Oportunidades abiertas del periodo';
  set('commercial-data-state', data.open_rule && data.delivery_rule ? 'Corte preparado' : 'Validaciones pendientes');
}

/** @param {Model} model @param {(id: string, value: string) => void} set */
function monthly(model, set) {
  const saved = model.monthly;
  const chart = node('monthly-profit-chart');
  const data = saved
    ? { ...saved, months: (saved.months || []).map((/** @type {any} */ row) => ({ ...row, margin: row.cost !== null && row.cost !== undefined && Number(row.revenue) > 0 ? ((Number(row.revenue) - Number(row.cost)) / Number(row.revenue)) * 100 : null })) }
    : null;
  if (data && chart) {
    mountMonthlyChart(chart, data);
    set('monthly-profit-state', data.complete ? 'Corte preparado' : 'Margen parcial · costos disponibles');
  } else if (chart) chart.textContent = 'El corte del periodo se está preparando. Las cifras no se actualizarán automáticamente.';
  set('monthly-profit-note', 'Facturación mensual = Invoiced + Collected (incluido factoring), por mes de DataRevenue G; no usa el monto total del proyecto. Costos por fecha de cada registro de Clockify. Fechas y conceptos de facturación pendientes de validar con Florencia. La línea muestra el margen con los costos disponibles; * indica un margen parcial que puede cambiar al completar costos.');
}

/**
 * Pinta todas las cifras del corte y devuelve lo que sigue cargando.
 * @param {Model} model
 * @returns {Set<string>}
 */
export function renderMetrics(model) {
  const loading = loadingIds(model);
  const set = setter(loading);
  financial(model, set);
  operations(model, set);
  commercial(model, set);
  monthly(model, set);
  renderCardVisuals(model);
  return loading;
}
