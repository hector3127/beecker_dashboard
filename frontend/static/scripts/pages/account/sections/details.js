// @ts-check
// Las ventanas «Ver más» de la cuenta: backlog, ROC, NPS y oportunidades.
import { el } from '#app/lib/dom.js';
import { element, filteredTable, hours, shape } from './modal.js';

/** @typedef {ReturnType<typeof import('./modal.js').createModal>} Detail */

/** @param {Detail} detail @param {any[]} opportunities */
export function openBacklog(detail, opportunities) {
  filteredTable(
    detail,
    'Backlog de la cuenta',
    ['Account Name', 'Opportunity Name', 'Delivery Manager', 'Opportunity Stage', 'Fecha de cierre', 'Total Hours'],
    opportunities.map((p) => [p.account, p.name, p.manager, p.stage, p.close, hours(p.hours)]),
    3,
  );
}

/** @param {Detail} detail @param {any[]} processes */
export function openRoc(detail, processes) {
  filteredTable(
    detail,
    'Procesos de la cuenta en ROC',
    ['Proceso', 'ID', 'Servicio', 'BOT ID', 'Estado'],
    processes.map((p) => [p.process, p.id || p.bot_id, p.service, p.bot_id, p.state]),
    4,
  );
}

/** Tarjeta de oportunidades abiertas. @param {any[]} opportunities @param {() => void} onMore */
export function renderOpportunities(opportunities, onMore) {
  const rows = opportunities.map((o) => el('div', { class: 'account-state' }, el('span', { text: o.name }), el('span', { text: o.stage })));
  return el(
    'section',
    { class: 'account-card account-opportunities' },
    el('h2', {}, 'Oportunidades de la cuenta ', el('button', { class: 'account-more', id: 'backlog-more', text: 'Ver más ↗', onclick: onMore })),
    ...(rows.length ? rows : [el('p', { class: 'account-muted', text: 'Sin oportunidades abiertas.' })]),
  );
}

/** NPS de todos los proyectos en una sola linea con desplazamiento. @param {Detail} detail @param {any[]} projects */
export function openNps(detail, projects) {
  const nps = projects.filter((p) => p.nps !== null && p.nps !== undefined);
  const root = detail.start('Satisfacción del cliente · NPS por proyecto');
  element('p', 'Todos los proyectos con NPS registrado; desliza horizontalmente para ver los IDs completos.', root, 'account-muted');
  element('h3', 'NPS por proyecto', root);
  const scroll = element('div', null, root, 'nps-full-scroll');
  const width = Math.max(1050, nps.length * 120);
  const chart = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  chart.setAttribute('viewBox', `0 0 ${width} 270`);
  chart.style.width = `${width}px`;
  chart.style.height = '270px';
  scroll.append(chart);
  const points = [];
  for (const value of [0, 25, 50, 75, 100]) {
    const y = 210 - value * 1.5;
    shape(chart, 'line', { x1: 28, x2: width - 20, y1: y, y2: y, stroke: '#e8eafa' });
    shape(chart, 'text', { x: 22, y: y + 3, 'text-anchor': 'end', 'font-size': 10, fill: '#8580a2' }, String(value));
  }
  nps.forEach((project, index) => {
    const x = 40 + index * 120;
    const y = 210 - Math.max(0, Math.min(100, Number(project.nps))) * 1.5;
    points.push(`${x},${y}`);
    const dot = shape(chart, 'circle', { cx: x, cy: y, r: 4, fill: '#6235f1' });
    shape(dot, 'title', {}, `${project.id} · ${project.name}: ${project.nps} NPS`);
    shape(chart, 'text', { x, y: 240, 'text-anchor': 'middle', 'font-size': 10, fill: '#8580a2' }, project.id);
  });
  shape(chart, 'polyline', { points: points.join(' '), stroke: '#6235f1', 'stroke-width': 2.5, fill: 'none' });
  element('p', 'Comparación entre proyectos; no es una tendencia mensual.', root, 'account-muted');
}
