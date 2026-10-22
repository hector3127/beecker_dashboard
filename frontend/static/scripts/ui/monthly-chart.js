// @ts-check
// Rentabilidad mensual: barras de facturacion y costos y linea de margen. Se
// redibuja cuando cambia el ancho del contenedor.
import { svg } from '#app/lib/dom.js';
import { formatCompact } from '#app/lib/format.js';
import { monthlyModel } from '#app/lib/monthly-model.js';

/**
 * @param {HTMLElement} container
 * @param {{months?: any[], complete?: boolean}} data
 */
export function mountMonthlyChart(container, data) {
  let width = 0;
  const render = () => {
    width = container.clientWidth || 900;
    const model = monthlyModel(data, width);
    const rows = data.months || [];
    const text = (/** @type {number} */ x, /** @type {number} */ y, /** @type {string} */ value, /** @type {string} */ cls = '', anchor = 'middle') => svg('text', { class: `axis ${cls}`, x, y, 'text-anchor': anchor }, value);
    const chart = svg('svg', { width: model.width, viewBox: `0 0 ${model.width} 275`, role: 'img', 'aria-label': 'Ingresos, costos y margen mensual. Montos en USD; margen en el eje derecho.' });
    chart.style.minWidth = `${model.width}px`;
    if (!rows.length) {
      chart.append(text(model.width / 2, 140, 'Sin datos para este periodo'));
      return container.replaceChildren(chart);
    }
    for (const tick of model.leftTicks) {
      chart.append(svg('line', { class: 'grid', x1: model.left, x2: model.width - model.right, y1: tick.y, y2: tick.y }), text(model.left - 6, tick.y + 4, formatCompact(tick.value), '', 'end'));
    }
    const long = rows.length > 12;
    model.columns.forEach((column, index) => {
      const date = new Date(`${column.month}-02T12:00:00`);
      chart.append(text(column.center, 250, date.toLocaleDateString('es-MX', long ? { month: 'short', year: '2-digit' } : { month: 'short' })));
      for (const [kind, bar, label] of /** @type {const} */ ([['revenue', column.revenue, 'Facturación'], ['cost', column.cost, 'Costos']])) {
        if (!bar) {
          chart.append(text((kind === 'revenue' ? column.center - 20 : column.center + 20), model.baseline - 8, model.step < 70 ? '—' : 'Pendiente'));
          continue;
        }
        const rect = svg('rect', { class: `bar-${kind}`, x: bar.x, y: bar.y, width: bar.width, height: bar.height, rx: 3 }, svg('title', {}, `${rows[index].month} · ${label}: ${formatCompact(bar.value)}`));
        chart.append(rect);
        if (model.step >= 105) chart.append(text(bar.x + bar.width / 2, Math.max(17, bar.y - 7), formatCompact(bar.value)));
      }
    });
    for (const tick of model.rightTicks) chart.append(text(model.width - model.right + 6, tick.y + 4, `${tick.value}%`, 'margin', 'start'));
    for (const points of model.segments) {
      chart.append(svg('polyline', { class: 'margin-line', fill: 'none', points: points.map((p) => `${p.x},${p.y}`).join(' ') }));
      for (const p of points) {
        chart.append(svg('circle', { class: 'margin-dot', cx: p.x, cy: p.y, r: 4 }, svg('title', {}, `${p.month} · Margen: ${p.value}%${data.complete ? '' : ' provisional'}`)));
        if (model.step >= 70) {
          const label = `${p.value.toLocaleString('es-MX', { maximumFractionDigits: 1 })}%${data.complete ? '' : '*'}`;
          chart.append(text(p.x, p.y < model.baseline - 25 ? p.y + 20 : Math.max(14, p.y - 12), label, 'margin halo'));
        }
      }
    }
    container.replaceChildren(chart);
  };
  render();
  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(() => container.clientWidth && container.clientWidth !== width && render()).observe(container);
  }
}
