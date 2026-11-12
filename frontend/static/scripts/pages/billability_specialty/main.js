// @ts-check
import { bindPeriodPicker } from '#app/ui/period-picker.js';
import { el } from '#app/lib/dom.js';

document.querySelectorAll('details.pf').forEach(picker => {
  bindPeriodPicker(/** @type {HTMLDetailsElement} */ (picker));
});

const data = JSON.parse(document.getElementById('specialty-chart-data')?.textContent || '[]');
const number = new Intl.NumberFormat('es-MX', {maximumFractionDigits: 2});
const colors = ['#3179c4', '#25a883', '#687384', '#302358', '#a99be1', '#e9a9c8'];

function stackedChart(id, series, valuesFor) {
  const target = document.getElementById(id);
  if (!target) return;
  if (!data.length) {
    target.append(el('p', {text: 'Sin datos para el periodo seleccionado.'}));
    return;
  }

  const points = data.map(month => series.map(({key}) => valuesFor(month, key)));
  const positive = Math.max(1, ...points.map(row => row.reduce((sum, n) => sum + Math.max(n, 0), 0)));
  const negative = Math.min(0, ...points.map(row => row.reduce((sum, n) => sum + Math.min(n, 0), 0)));
  const step = Math.max(1, Math.ceil((positive - negative) / 5));
  const top = Math.ceil(positive / step) * step;
  const bottom = Math.floor(negative / step) * step;
  const height = top - bottom;
  const percent = value => `${(value - bottom) / height * 100}%`;
  const plot = el('div', {class: 'specialty-chart-plot'});
  for (let tick = bottom; tick <= top; tick += step) {
    const grid = el('div', {class: tick === 0 ? 'specialty-chart-zero' : 'specialty-chart-grid'});
    grid.style.bottom = percent(tick);
    grid.append(el('span', {text: String(tick)}));
    plot.append(grid);
  }
  const bars = el('div', {class: 'specialty-chart-bars'});
  data.forEach((month, index) => {
    const values = points[index];
    const description = series.map(({label}, i) => `${label} ${number.format(values[i])}`).join(', ');
    const bar = el('div', {class: 'specialty-chart-bar', role: 'img', 'aria-label': `${month.month}, ${description}`});
    let up = 0, down = 0;
    values.forEach((value, i) => {
      if (!value) return;
      const segment = el('div', {class: value < 0 ? 'specialty-chart-segment is-deficit' : 'specialty-chart-segment', title: `${month.month} · ${series[i].label}: ${number.format(value)}`});
      segment.style.bottom = percent(value > 0 ? up : down + value);
      segment.style.height = `${Math.abs(value) / height * 100}%`;
      segment.style.backgroundColor = series[i].color;
      bar.append(segment);
      if (value > 0) up += value;
      else down += value;
    });
    bar.append(el('span', {class: 'specialty-chart-month', text: month.label}));
    bars.append(bar);
  });
  plot.append(bars);
  const legend = el('div', {class: 'specialty-chart-legend'});
  for (const item of series) {
    const swatch = el('i', {'aria-hidden': 'true'});
    swatch.style.backgroundColor = item.color;
    legend.append(el('span', {}, swatch, item.label));
  }
  const scroll = el('div', {class: 'specialty-chart-scroll', tabindex: '0'}, plot);
  plot.style.minWidth = `${Math.max(250, data.length * 32)}px`;
  target.append(legend, el('div', {class: 'specialty-chart-unit', text: 'Personas equivalentes'}), scroll);
}

stackedChart('specialty-assignment-chart', [
  {key: 'fixed', label: 'HC fijo', color: '#5140ad'},
  {key: 'variable', label: 'HC variable', color: '#a99be1'},
  {key: 'free', label: 'HC libre', color: '#ee7246'},
], (month, key) => month[key]);

const roles = [...new Set(data.flatMap(month => Object.keys(month.roles)))];
stackedChart('specialty-availability-chart',
  roles.map((name, index) => ({key: name, label: name, color: colors[index % colors.length]})),
  (month, key) => month.roles[key] ?? 0);
