// @ts-check
// Consumo por mes (C) de cada Delivery Manager: curvas seleccionables y escala
// ampliada o completa.
import { el, svg } from '#app/lib/dom.js';
import { chartScale, seriesPath } from '#app/lib/kpi-chart.js';

const LEFT = 45;
const RIGHT = 535;
const TOP = 16;
const BOTTOM = 234;

/**
 * @param {HTMLElement} container
 * @param {{labels: string[], series: {name: string, values: (number | null)[]}[], highlight?: string[]}} data
 */
export function renderChart(container, data) {
  let complete = false;
  /** @type {number | null} */
  let selected = null;
  const chart = svg('svg', { id: 'kpi-chart', viewBox: '0 0 560 270', role: 'img', 'aria-label': 'Consumo de horas sobre presupuesto (C) por mes de cada Delivery Manager' });
  const legend = el('div', { id: 'kpi-legend', class: 'kpi-legend' });
  const scaleText = el('span', { id: 'kpi-chart-scale', role: 'status' });
  const toggle = el('button', { id: 'kpi-chart-toggle', type: 'button', 'aria-pressed': 'false', onclick: () => ((complete = !complete), draw()) });
  const count = data.labels.length;
  const step = count > 1 ? (RIGHT - LEFT) / (count - 1) : 0;
  const x = (/** @type {number} */ i) => (count > 1 ? LEFT + i * step : (LEFT + RIGHT) / 2);
  const buttons = data.series.map((serie, index) =>
    el('button', { type: 'button', 'aria-pressed': 'false', onclick: () => ((selected = selected === index ? null : index), draw()) }, el('i', { class: `s${index % 6}`, 'aria-hidden': 'true' }), serie.name),
  );
  legend.append(...buttons);

  function draw() {
    const shown = data.series.filter((_, i) => selected === null || selected === i);
    const scale = chartScale(shown.flatMap((s) => s.values), complete);
    const y = (/** @type {number} */ v) => BOTTOM - ((v - scale.minimum) / (scale.maximum - scale.minimum)) * (BOTTOM - TOP);
    scaleText.textContent = `${complete ? 'Escala completa: ' : 'Escala ampliada: '}${scale.minimum}–${scale.maximum}%`;
    toggle.textContent = complete ? 'Ampliar diferencias' : 'Ver escala completa';
    toggle.setAttribute('aria-pressed', String(complete));
    chart.replaceChildren();
    for (const tick of scale.ticks) {
      chart.append(svg('line', { class: 'grid', x1: LEFT, x2: RIGHT, y1: y(tick), y2: y(tick) }), svg('text', { class: 'axis', x: LEFT - 7, y: y(tick) + 4, 'text-anchor': 'end' }, `${tick}%`));
    }
    data.labels.forEach((label, i) => {
      if ((data.highlight || []).includes(label)) {
        const width = count > 1 ? step : 80;
        const start = Math.max(LEFT, x(i) - width / 2);
        chart.append(svg('rect', { class: 'highlight', x: start, y: TOP, width: Math.min(RIGHT, x(i) + width / 2) - start, height: BOTTOM - TOP, rx: 4 }));
      }
      chart.append(svg('text', { class: 'axis', x: x(i), y: 256, 'text-anchor': 'middle' }, label));
    });
    data.series.forEach((serie, index) => {
      if (selected !== null && selected !== index) return;
      chart.append(svg('path', { class: `line s${index % 6}`, d: seriesPath(serie.values, x, y), fill: 'none' }));
      serie.values.forEach((value, i) => {
        if (value == null || !Number.isFinite(value)) return;
        chart.append(svg('circle', { class: `dot s${index % 6}`, cx: x(i), cy: y(value), r: 3.5 }, svg('title', {}, `${serie.name} · ${data.labels[i]}: ${value}%`)));
      });
    });
    if (!scale.hasValues) chart.append(svg('text', { class: 'axis', x: 290, y: 125, 'text-anchor': 'middle' }, 'Sin valores para este periodo'));
    buttons.forEach((b, i) => {
      b.setAttribute('aria-pressed', String(selected === i));
      b.classList.toggle('dim', selected !== null && selected !== i);
    });
  }

  container.append(
    el('div', { class: 'kpi-chart-tools' }, scaleText, toggle),
    chart,
    legend,
    el('p', { class: 'note', text: 'Selecciona un DM para ver su curva; pulsa otra vez para comparar todos. La escala ampliada muestra las diferencias sin cambiar los porcentajes.' }),
  );
  draw();
}
