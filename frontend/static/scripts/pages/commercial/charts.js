// @ts-check
import { el, svg } from '#app/lib/dom.js';
import { loadAccountLogos, findAccountLogo } from '#app/lib/account-logos.js';

const palette = ['#7524f3', '#4d54ef', '#21bbed', '#00bd8a', '#f6bf20', '#bb85ed'];
const fmt = (n, digits = 0) => Number(n || 0).toLocaleString('es-MX', { maximumFractionDigits: digits });
const node = document.getElementById('commercial-chart-data');
const data = node ? JSON.parse(node.textContent || '{}') : null;

if (data) {
  document.querySelectorAll('.k4 .kx').forEach((card, i) => {
    const values = data.sparklines[i] || [];
    if (!values.some((n) => n > 0)) return;
    const chart = svg('svg', { viewBox: '0 0 110 45', class: 'commercial-kpi-spark', role: 'img', 'aria-label': `Distribución mensual ${data.year}` });
    const max = Math.max(...values, 1);
    const points = values.map((v, n) => `${n * 10},${40 - v / max * 34}`);
    chart.append(svg('title', {}, `Distribución mensual del año ${data.year}; no representa una variación porcentual.`));
    chart.append(svg('path', { d: `M0 45 L${points.join(' L')} L110 45Z`, fill: palette[i], opacity: '.1' }));
    chart.append(svg('polyline', { points: points.join(' '), fill: 'none', stroke: i === 3 ? '#ef43b3' : palette[i], 'stroke-width': '1.7', 'stroke-linejoin': 'round' }));
    card.append(chart);
  });

  const mount = document.getElementById('commercial-stage-donut');
  if (mount) {
    const rows = data.stages.slice(0, 5).map((g) => ({ ...g }));
    const others = data.stages.slice(5).reduce((n, g) => n + g.count, 0);
    if (others) rows.push({ display_name: 'Otros', count: others });
    const chart = svg('svg', { viewBox: '0 0 170 170', role: 'img', 'aria-label': `${fmt(data.count)} oportunidades distribuidas por etapa` });
    chart.append(svg('circle', { cx: 85, cy: 85, r: 64, fill: 'none', stroke: '#eee7ff', 'stroke-width': 28 }));
    let offset = 0;
    const legend = el('div', { class: 'commercial-donut-legend' });
    rows.forEach((group, i) => {
      const percentage = data.count ? group.count / data.count * 100 : 0;
      const arc = svg('circle', { cx: 85, cy: 85, r: 64, fill: 'none', stroke: palette[i], 'stroke-width': 28, pathLength: 100, 'stroke-dasharray': `${percentage} ${100 - percentage}`, 'stroke-dashoffset': -offset, transform: 'rotate(-90 85 85)' });
      arc.append(svg('title', {}, `${group.display_name || group.name}: ${fmt(group.count)} registros (${fmt(percentage, 1)}%)`));
      chart.append(arc);offset += percentage;
      const dot = el('i');dot.style.backgroundColor = palette[i];
      legend.append(el('div', {}, dot, el('span', { text: group.display_name || group.name, title: group.display_name || group.name }), el('b', { text: `${fmt(percentage, 1)}%` })));
    });
    chart.append(svg('text', { x: 85, y: 84, 'text-anchor': 'middle', fill: '#160852', 'font-size': 22, 'font-weight': 800 }, fmt(data.count)));
    chart.append(svg('text', { x: 85, y: 102, 'text-anchor': 'middle', fill: '#4e367c', 'font-size': 10 }, 'Oportunidades'));
    mount.replaceChildren(chart, legend);
  }

  const host = document.getElementById('commercial-pipeline-chart');
  function drawHours() {
    if (!host) return;
    const monthly = document.querySelector('[data-chart-mode="month"]')?.getAttribute('aria-pressed') === 'true';
    const selected = Number(/** @type {HTMLSelectElement|null} */ (document.getElementById('commercial-chart-month'))?.value || 0);
    const indices = monthly ? [selected] : data.months.map((_, i) => i);
    const values = indices.map((i) => Number(data.hours[i] || 0));
    const maximum = Math.max(1, ...values);
    const magnitude = Math.pow(10, Math.floor(Math.log10(maximum / 5)));
    const step = Math.ceil(maximum / 5 / magnitude) * magnitude;
    const ceiling = step * 5;
    const chart = svg('svg', { viewBox: '0 0 900 260', role: 'img', 'aria-label': `Horas de alta probabilidad por mes de cierre ${data.year}` });
    const defs = svg('defs');
    const gradient = svg('linearGradient', { id: 'commercial-hours-gradient', x1: '0', y1: '0', x2: '0', y2: '1' });
    gradient.append(svg('stop', { offset: '0%', 'stop-color': '#b775ff' }), svg('stop', { offset: '100%', 'stop-color': '#7024e8' }));defs.append(gradient);chart.append(defs);
    const left = 65, right = 845, top = 25, bottom = 217;
    for (let i = 0; i <= 5; i++) {
      const y = bottom - i / 5 * (bottom - top);
      chart.append(svg('line', { x1: left, x2: right, y1: y, y2: y, stroke: '#e7ddfa', 'stroke-dasharray': i ? '3 3' : '0' }));
      chart.append(svg('text', { x: left - 10, y: y + 4, 'text-anchor': 'end', 'font-size': 11, fill: '#614b8c' }, `${fmt(step * i)} h`));
      chart.append(svg('text', { x: right + 10, y: y + 4, 'font-size': 11, fill: '#e02695' }, `${i * 20}%`));
    }
    const gap = (right - left) / Math.max(1, indices.length);
    let line = [];
    function flush() {
      if (line.length > 1) chart.append(svg('polyline', { points: line.join(' '), fill: 'none', stroke: '#f32e9c', 'stroke-width': 2 }));
      line = [];
    }
    indices.forEach((month, i) => {
      const x = left + (i + .5) * gap;
      const hours = Number(data.hours[month] || 0);
      const y = bottom - hours / ceiling * (bottom - top);
      const width = Math.min(45, gap * .76);
      const bar = svg('rect', { x: x - width / 2, y, width, height: bottom - y, rx: 5, fill: 'url(#commercial-hours-gradient)' });
      bar.append(svg('title', {}, `${data.months[month]}: ${fmt(hours, 2)} horas`));chart.append(bar);
      chart.append(svg('text', { x, y: y - 7, 'text-anchor': 'middle', 'font-size': 11, 'font-weight': 700, fill: '#301175' }, fmt(hours)));
      chart.append(svg('text', { x, y: bottom + 22, 'text-anchor': 'middle', 'font-size': 12, fill: '#43316e' }, data.months[month]));
      const probability = data.probabilities[month];
      if (probability === null || probability === undefined) { flush();return; }
      const py = bottom - probability / 100 * (bottom - top);
      line.push(`${x},${py}`);
      const dot = svg('circle', { cx: x, cy: py, r: 3, fill: '#fff', stroke: '#f32e9c', 'stroke-width': 1.8 });
      dot.append(svg('title', {}, `${data.months[month]}: probabilidad media ponderada por horas ${fmt(probability, 1)}%`));chart.append(dot);
    });
    flush();
    const legend = el('div', { class: 'commercial-chart-legend' }, el('span', {}, el('i'), 'Horas'), el('span', {}, el('i', { class: 'probability-key' }), 'Probabilidad media ponderada por horas'));
    host.replaceChildren(chart, legend);
  }
  drawHours();
  document.querySelectorAll('[data-chart-mode]').forEach((button) => button.addEventListener('click', () => {
    document.querySelectorAll('[data-chart-mode]').forEach((b) => b.setAttribute('aria-pressed', String(b === button)));
    const month = document.getElementById('commercial-chart-month');if (month) month.hidden = button.getAttribute('data-chart-mode') !== 'month';
    drawHours();
  }));
  document.getElementById('commercial-chart-month')?.addEventListener('change', drawHours);
}

loadAccountLogos().then((items) => document.querySelectorAll('[data-account-logo]').forEach((holder) => {
  const logo = findAccountLogo(items, holder.getAttribute('data-account-logo'));
  if (!logo) return;
  const img = el('img', { src: logo.url, alt: '', loading: 'lazy' });
  img.addEventListener('error', () => holder.replaceChildren(holder.getAttribute('data-account-logo')?.slice(0, 1) || ''));
  holder.replaceChildren(img);
}));

