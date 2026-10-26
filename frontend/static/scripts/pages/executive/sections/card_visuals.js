// Visuals use the selected cut only; decorative header art has no data meaning.
import { svg } from '#app/lib/dom.js';

const numeric = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));

function gauge(id, value) {
  const target = document.getElementById(id);
  if (!target) return;
  const host = target.parentElement;
  host.querySelector(`[data-gauge="${id}"]`)?.remove();
  if (!numeric(value)) return;
  const amount = Math.max(0, Math.min(100, Number(value)));
  host.append(svg('svg', { class: 'metric-gauge', viewBox: '0 0 150 9', 'aria-hidden': 'true', 'data-gauge': id },
    svg('rect', { width: 150, height: 9, rx: 4.5, fill: 'currentColor', opacity: .12 }),
    svg('rect', { width: amount * 1.5, height: 9, rx: 4.5, fill: 'currentColor', opacity: .75 }),
  ));
}

function monthly(id, months, margin = false) {
  const target = document.getElementById(id);
  if (!target) return;
  const host = target.parentElement;
  host.querySelector('.metric-visual')?.remove();
  host.classList.remove('has-metric-visual');
  const values = months.map((row) => {
    if (!numeric(row.revenue)) return null;
    if (!margin) return Number(row.revenue);
    return numeric(row.cost) && Number(row.revenue) > 0
      ? (Number(row.revenue) - Number(row.cost)) / Number(row.revenue) * 100 : null;
  });
  if (values.filter((n) => n !== null).length < 2) return;
  const valid = values.filter((n) => n !== null);
  const low = Math.min(0, ...valid), high = Math.max(0, ...valid);
  const range = high - low || 1;
  const y = (n) => 39 - (n - low) / range * 32;
  const chart = svg('svg', { class: 'metric-visual', viewBox: '0 0 96 44', role: 'img',
    'aria-label': margin ? 'Margen mensual con los costos disponibles del periodo seleccionado' : 'Facturación mensual del periodo seleccionado' });
  chart.append(svg('title', {}, margin ? 'Margen mensual del periodo; las ausencias de costos interrumpen la línea.' : 'Facturación mensual del periodo seleccionado.'));
  if (margin) {
    let path = '', connected = false;
    values.forEach((value, index) => {
      if (value === null) { connected = false; return; }
      const x = 4 + index / Math.max(1, values.length - 1) * 88;
      path += `${connected ? 'L' : 'M'}${x},${y(value)} `;
      connected = true;
    });
    chart.append(svg('path', { d: path, fill: 'none', stroke: 'currentColor', 'stroke-width': 2.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
  } else {
    const step = 88 / values.length;
    values.forEach((value, index) => {
      if (value === null) return;
      const a = y(value), b = y(0);
      chart.append(svg('rect', { x: 4 + index * step, y: Math.min(a, b), width: Math.max(1, step * .65), height: Math.max(1, Math.abs(b - a)), rx: 1.5, fill: 'currentColor' }));
    });
  }
  host.classList.add('has-metric-visual');
  host.append(chart);
}

export function renderCardVisuals(model) {
  monthly('executive-revenue', model.monthly?.months || []);
  monthly('executive-margin', model.monthly?.months || [], true);
  gauge('executive-collections', model.revenue?.collections_percent);
  gauge('executive-ops-advance', model.operations?.advance);
  gauge('executive-ops-facturability', model.operations?.facturability);
}
