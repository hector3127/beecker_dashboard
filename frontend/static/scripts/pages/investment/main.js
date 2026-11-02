// @ts-check
// Inversión acumulada de los proyectos activos; barras y detalle por persona.
import { watchLoadingMessages } from '#app/ui/portal-loading.js';

watchLoadingMessages();
document.querySelectorAll('[data-width]').forEach((node) => {
  /** @type {HTMLElement} */ (node).style.width = `${/** @type {HTMLElement} */ (node).dataset.width}%`;
});
// Gráficas SVG con datos reales; sin librerías ni estilos en línea.
import { svg } from '#app/lib/dom.js';
import { mountResourceDetail } from './resource_detail.js?v=20261031-accumulated';
import { formatNumber } from '#app/lib/format.js';
const dataNode = document.getElementById('investment-chart-data');
const chartData = dataNode ? JSON.parse(dataNode.textContent || '{}') : null;
const fmt = (n) => formatNumber(n, 1);
if (chartData) {
  const history = chartData.history || [];
  const maxValue = Math.max(0, ...history.flatMap((m) => [m.operational || 0, m.commercial || 0]));
  const step = Math.max(1, Math.ceil(maxValue / 5 / Math.pow(10, Math.floor(Math.log10(maxValue || 1)) - 1))) * Math.pow(10, Math.floor(Math.log10(maxValue || 1)) - 1);
  const ceiling = Math.max(1, step * 5);
  const chart = svg('svg', { viewBox: '0 0 720 255', role: 'img', 'aria-label': 'Evolución acumulada de inversión de los proyectos activos de EVA 1 y EVA 3' });
  const defs = svg('defs');
  for (const [id, first, last] of [['inv-green', '#38d7a4', '#00b77e'], ['inv-purple', '#a45cff', '#7021f2']]) {
    defs.append(svg('linearGradient', { id, x1: 0, y1: 0, x2: 0, y2: 1 }, svg('stop', { offset: '0%', 'stop-color': first }), svg('stop', { offset: '100%', 'stop-color': last })));
  }
  chart.append(defs);
  for (let i = 0; i <= 5; i++) {
    const y = 212 - i * 38;
    chart.append(svg('line', { x1: 53, x2: 705, y1: y, y2: y, stroke: '#dcd3f7', 'stroke-dasharray': '3 3' }),
      svg('text', { x: 42, y: y + 4, 'text-anchor': 'end', fill: '#68598c', 'font-size': 12 }, fmt(ceiling * i / 5) + ' h'));
  }
  history.forEach((month, index) => {
    const x = 67 + index * 108;
    for (const [kind, dx, color, label] of [['operational', 0, 'inv-green', 'Operativa'], ['commercial', 41, 'inv-purple', 'Comercial']]) {
      const value = month[kind];
      if (typeof value !== 'number') continue;
      const height = value / ceiling * 190;
      chart.append(svg('rect', { x: x + dx, y: 212 - height, width: 37, height, rx: 5, fill: `url(#${color})` },
        svg('title', {}, `${month.month} · ${label}: ${fmt(value)} h`)));
    }
    chart.append(svg('text', { x: x + 37, y: 237, 'text-anchor': 'middle', fill: '#51427b', 'font-size': 13 }, month.label));
    if (month.error) chart.append(svg('text', { x: x + 37, y: 205, 'text-anchor': 'middle', fill: '#9a789f', 'font-size': 11 }, 'Sin datos'));
  });
  document.getElementById('inv-history-chart')?.append(chart);
  const operational = chartData.operational || 0, commercial = chartData.commercial || 0;
  const total = operational + commercial;
  const circle = svg('svg', { viewBox: '0 0 230 230', role: 'img', 'aria-label': `Distribución: ${fmt(operational)} horas operativas y ${fmt(commercial)} comerciales` });
  const circumference = 2 * Math.PI * 83;
  circle.append(svg('circle', { cx: 115, cy: 115, r: 83, fill: 'none', stroke: '#e9e2f7', 'stroke-width': 34 }));
  if (total > 0) {
    const green = operational / total * circumference;
    circle.append(svg('circle', { cx: 115, cy: 115, r: 83, fill: 'none', stroke: '#00c389', 'stroke-width': 34, 'stroke-dasharray': `${green} ${circumference}`, transform: 'rotate(-90 115 115)' }),
      svg('circle', { cx: 115, cy: 115, r: 83, fill: 'none', stroke: '#8330ff', 'stroke-width': 34, 'stroke-dasharray': `${circumference - green} ${circumference}`, 'stroke-dashoffset': -green, transform: 'rotate(-90 115 115)' }));
  }
  circle.append(svg('text', { x: 115, y: 109, 'text-anchor': 'middle', fill: '#171048', 'font-size': 25, 'font-weight': 800 }, `${formatNumber(total, 0)} h`),
    svg('text', { x: 115, y: 136, 'text-anchor': 'middle', fill: '#746493', 'font-size': 15 }, 'Total'));
  document.getElementById('inv-donut')?.append(circle);
}
// Encabezados con el mismo sistema de iconos de trazo de la página.
const paths = [
  ['.inv-history .inv-chip', 'M5 20V11M10 20V5M15 20V9M20 20V2'],
  ['.inv-distribution .inv-chip', 'M12 2v10h10M9 3a9 9 0 1 0 12 12M15 2a9 9 0 0 1 7 7h-7Z'],
  ['.inv-specialties .inv-chip', 'M3 20v-2c0-5 12-5 12 0v2M6 8a3 3 0 1 0 6 0a3 3 0 1 0-6 0M17 6a3 3 0 0 1 0 6M18 15c3 0 4 2 4 5'],
  ['.inv-commercial-types .inv-chip', 'M3 4h18l-7 9v6l-4 2v-8Z'],
  ['.inv-resources .inv-chip', 'M5 21v-3c0-5 14-5 14 0v3M8 7a4 4 0 1 0 8 0a4 4 0 1 0-8 0'],
];
for (const [selector, d] of paths) document.querySelector(selector)?.replaceChildren(svg('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, svg('path', { d })));

mountResourceDetail();
