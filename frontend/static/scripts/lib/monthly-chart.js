// @ts-check
// Rentabilidad mensual: barras de facturacion y costos y linea de margen.
// El modelo es puro (se prueba sin navegador); mountMonthlyChart lo dibuja.
import { svg } from '#app/lib/dom.js';
import { formatCompact } from '#app/lib/format.js';

const TOP = 32;
const BASELINE = 222;
const HEIGHT = 275;

/**
 * @typedef {object} Primitive
 * @property {'line' | 'rect' | 'text' | 'polyline' | 'circle'} tag
 * @property {Record<string, string | number>} attrs
 * @property {string} [text]
 * @property {string} [title]
 */

/**
 * @param {{months?: any[], complete?: boolean}} data
 * @param {number} viewportWidth Ancho disponible; el grafico crece si hay muchos meses.
 * @returns {{width: number, label: string, items: Primitive[]}}
 */
export function monthlyChartModel(data, viewportWidth) {
  const rows = data.months || [];
  const viewport = Math.max(240, Number(viewportWidth) || 900);
  const width = rows.length > 6 ? Math.max(viewport, 120 + rows.length * 84) : viewport;
  const left = viewport < 500 ? 53 : 72;
  const right = viewport < 500 ? 43 : 55;
  const plot = width - left - right;
  const step = plot / Math.max(1, rows.length);
  const barWidth = Math.max(6, Math.min(36, (step - 12) / 2));
  /** @type {Primitive[]} */
  const items = [];
  const text = (/** @type {number} */ x, /** @type {number} */ y, /** @type {string} */ value, color = '#4A4D86', anchor = 'middle', extra = {}) =>
    items.push({ tag: 'text', attrs: { x, y, 'text-anchor': anchor, fill: color, 'font-size': 11, ...extra }, text: value });
  const label = 'Ingresos, costos y margen mensual. Montos en USD; margen en el eje derecho.';
  if (!rows.length) {
    text(width / 2, 140, 'Sin datos para este periodo');
    return { width, label, items };
  }
  const values = rows.flatMap((row) => [row.revenue, row.cost ?? 0]);
  const maximum = Math.max(1, ...values);
  const minimum = Math.min(0, ...values);
  const range = maximum - minimum;
  const y = (/** @type {number} */ value) => BASELINE - ((value - minimum) * (BASELINE - TOP)) / range;
  const zero = y(0);
  const margins = rows.filter((row) => row.margin !== null && row.margin !== undefined).map((row) => row.margin);
  const marginMin = Math.min(0, ...margins);
  const marginMax = Math.max(100, ...margins);
  const my = (/** @type {number} */ value) => BASELINE - ((value - marginMin) * (BASELINE - TOP)) / (marginMax - marginMin);
  for (let i = 0; i <= 3; i++) {
    const yy = BASELINE - (i * (BASELINE - TOP)) / 3;
    items.push({ tag: 'line', attrs: { x1: left, x2: width - right, y1: yy, y2: yy, stroke: '#ECEEFA' } });
    text(left - 6, yy + 4, formatCompact(minimum + (range * i) / 3), '#4A4D86', 'end');
  }
  /** @type {{x: number, y: number, value: number, month: string}[][]} */
  const segments = [];
  /** @type {{x: number, y: number, value: number, month: string}[]} */
  let segment = [];
  rows.forEach((row, i) => {
    const center = left + step * (i + 0.5);
    const x = center - barWidth - 2;
    const name = new Date(`${row.month}-02T12:00:00`).toLocaleDateString('es-MX', rows.length > 12 ? { month: 'short', year: '2-digit' } : { month: 'short' });
    const bar = (/** @type {number} */ xx, /** @type {number | null} */ value, /** @type {string} */ color, /** @type {string} */ kind) => {
      if (value === null || value === undefined) {
        text(xx + barWidth / 2, BASELINE - 8, step < 70 ? '—' : 'Pendiente');
        return;
      }
      const yy = Math.min(zero, y(value));
      items.push({ tag: 'rect', attrs: { x: xx, y: yy, width: barWidth, height: Math.abs(zero - y(value)), rx: 3, fill: color }, title: `${row.month} · ${kind}: ${formatCompact(value)}` });
      if (step >= 105) text(xx + barWidth / 2, Math.max(17, yy - 7), formatCompact(value), '#2A2D7A');
    };
    bar(x, row.revenue, '#8B5CF6', 'Facturación');
    bar(center + 2, row.cost, '#C9BDF2', 'Costos');
    text(center, 250, name);
    if (row.margin !== null && row.margin !== undefined) segment.push({ x: center, y: my(row.margin), value: row.margin, month: row.month });
    else if (segment.length) {
      segments.push(segment);
      segment = [];
    }
  });
  if (segment.length) segments.push(segment);
  if (margins.length) {
    for (let i = 0; i <= 3; i++) {
      text(width - right + 6, BASELINE - (i * (BASELINE - TOP)) / 3 + 4, `${Math.round(marginMin + ((marginMax - marginMin) * i) / 3)}%`, '#F0489E', 'start');
    }
    for (const points of segments) {
      items.push({ tag: 'polyline', attrs: { points: points.map((p) => `${p.x},${p.y}`).join(' '), fill: 'none', stroke: '#F0489E', 'stroke-width': 3 } });
      for (const p of points) {
        items.push({ tag: 'circle', attrs: { cx: p.x, cy: p.y, r: 4, fill: '#F0489E' }, title: `${p.month} · Margen: ${p.value}%${data.complete ? '' : ' provisional'}` });
        if (step >= 70) {
          const shown = `${Number(p.value).toLocaleString('es-MX', { maximumFractionDigits: 1 })}%${data.complete ? '' : '*'}`;
          text(p.x, p.y < BASELINE - 25 ? p.y + 20 : Math.max(14, p.y - 12), shown, '#C92C7E', 'middle', { 'paint-order': 'stroke', stroke: '#fff', 'stroke-width': 4, 'stroke-linejoin': 'round' });
        }
      }
    }
  }
  return { width, label, items };
}

/** Dibuja el modelo en un <svg>. @param {ReturnType<typeof monthlyChartModel>} model */
export function chartElement(model) {
  const root = svg('svg', { width: model.width, viewBox: `0 0 ${model.width} ${HEIGHT}`, role: 'img', 'aria-label': model.label });
  root.style.minWidth = `${model.width}px`;
  for (const item of model.items) {
    const node = svg(item.tag, item.attrs, ...(item.text === undefined ? [] : [item.text]));
    if (item.title) node.appendChild(svg('title', {}, item.title));
    root.appendChild(node);
  }
  return root;
}

/**
 * Monta el grafico y lo redibuja cuando cambia el ancho del contenedor.
 * @param {HTMLElement} container
 * @param {{months?: any[], complete?: boolean}} data
 */
export function mountMonthlyChart(container, data) {
  let width = 0;
  const draw = () => {
    width = container.clientWidth || 900;
    container.replaceChildren(chartElement(monthlyChartModel(data, width)));
  };
  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(() => {
      if (container.clientWidth && container.clientWidth !== width) draw();
    }).observe(container);
  }
  draw();
}
