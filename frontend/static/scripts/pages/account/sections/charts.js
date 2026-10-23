// @ts-check
// Tarjetas de la cuenta: modelos de servicio, consumo por servicio, estados,
// satisfaccion y alertas.
import { serviceModels, stateSlices } from '#app/lib/account-summary.js';
import { el, svg } from '#app/lib/dom.js';

/** @param {string} title @param {Node[]} body @param {Node[]} [heading] */
const card = (title, body, heading = []) => el('section', { class: 'account-card' }, el('h2', {}, title, ...heading), ...body);

/** Boton «Ver más» al lado del titulo. @param {string} id @param {() => void} onclick */
const more = (id, onclick) => [' ', el('button', { class: 'account-more', id, text: 'Ver más ↗', onclick })];

/** @param {number} percent @param {string} color */
function segment(percent, color) {
  const bar = el('i', { text: percent > 10 ? `${percent}%` : '' });
  bar.style.width = `${percent}%`;
  bar.style.background = color;
  return bar;
}

/** @param {any[]} projects */
function models(projects) {
  return card('Avance de proyectos por modelo de servicio', [
    ...serviceModels(projects).map((group) =>
      el(
        'div',
        { class: 'model-row' },
        el('span', { text: group.name }),
        el('div', { class: 'model-track' }, segment(group.completed, '#6540ed'), segment(group.other, '#c6b5fa'), segment(group.risk, '#ff8ca7')),
        el('b', { text: group.count }),
      ),
    ),
    el('p', { class: 'account-muted', text: '● Completados · ● Otras etapas · ● Con alertas' }),
  ]);
}

/** @param {() => void} onMore */
function consumption(onMore) {
  const legend = (/** @type {string} */ color, /** @type {string} */ text) => {
    const dot = el('i');
    dot.style.background = color;
    return el('span', {}, dot, text);
  };
  return card(
    'Consumo de horas vs. presupuesto',
    [
      el('div', { class: 'account-service-chart' }),
      el('div', { class: 'account-legend' }, legend('#d2c3fb', 'Presupuesto'), legend('#7450ed', 'Consumo')),
      el('p', { class: 'account-muted', text: 'Por servicio · acumulado de los proyectos' }),
    ],
    more('budget-more', onMore),
  );
}

/** @param {any[]} projects */
function states(projects) {
  const slices = stateSlices(projects);
  const ring = svg(
    'svg',
    { viewBox: '0 0 120 120', 'aria-label': 'Distribución de proyectos' },
    svg(
      'g',
      { transform: 'rotate(-90 60 60)', fill: 'none', 'stroke-width': 13 },
      ...slices.map((s) => svg('circle', { cx: 60, cy: 60, r: 43, pathLength: 100, stroke: s.color, 'stroke-dasharray': `${s.dash} 100`, 'stroke-dashoffset': s.offset })),
    ),
    svg('text', { x: 60, y: 60, 'text-anchor': 'middle', fill: '#21135c', 'font-size': 21, 'font-weight': 700 }, String(projects.length)),
    svg('text', { x: 60, y: 76, 'text-anchor': 'middle', fill: '#8a7da8', 'font-size': 9 }, 'proyectos'),
  );
  const legend = el(
    'div',
    {},
    ...slices.map((s) => {
      const dot = el('i');
      dot.style.background = s.color;
      return el('p', {}, dot, `${s.name} `, el('b', { text: `${s.count} (${s.percent}%)` }));
    }),
  );
  return card('Proyectos por estado', [el('div', { class: 'state-chart' }, ring, legend)]);
}

/** @param {string} tag @param {Record<string, string | number>} attrs @param {string} [text] */
const shape = (tag, attrs, text) => svg(tag, attrs, ...(text === undefined ? [] : [text]));

/** Dona y linea de NPS por proyecto; solo si hay proyectos con NPS. @param {any[]} nps */
function drawNps(nps, ringHost, lineHost) {
  if (!nps.length) return;
  const average = nps.reduce((sum, p) => sum + Number(p.nps), 0) / nps.length;
  const ring = shape('svg', { viewBox: '0 0 120 120' });
  ring.append(
    shape('circle', { cx: 60, cy: 60, r: 43, fill: 'none', stroke: '#e5e9ef', 'stroke-width': 13 }),
    shape('circle', { cx: 60, cy: 60, r: 43, fill: 'none', stroke: '#2dbc83', 'stroke-width': 13, pathLength: 100, 'stroke-dasharray': `${Math.max(0, Math.min(100, average))} 100`, transform: 'rotate(-90 60 60)' }),
    shape('text', { x: 60, y: 60, 'text-anchor': 'middle', 'font-size': 20, 'font-weight': 800, fill: '#211345' }, String(Math.round(average))),
    shape('text', { x: 60, y: 76, 'text-anchor': 'middle', 'font-size': 8, fill: '#9484b1' }, 'NPS promedio'),
  );
  ringHost.append(ring);
  const subset = nps.slice(0, 6);
  const points = [];
  for (const value of [0, 25, 50, 75, 100]) {
    const y = 115 - value;
    lineHost.append(shape('line', { x1: 24, x2: 425, y1: y, y2: y, stroke: '#eee8fc' }), shape('text', { x: 20, y: y + 3, 'text-anchor': 'end', 'font-size': 7, fill: '#9484b1' }, String(value)));
  }
  subset.forEach((p, i) => {
    const x = 35 + (i * 375) / Math.max(1, subset.length - 1);
    const y = 115 - Math.max(0, Math.min(100, Number(p.nps)));
    points.push(`${x},${y}`);
    lineHost.append(shape('circle', { cx: x, cy: y, r: 3, fill: '#6e3fed' }), shape('text', { x, y: 137, 'text-anchor': 'middle', 'font-size': 7, fill: '#9484b1' }, p.id));
  });
  lineHost.append(shape('polyline', { points: points.join(' '), fill: 'none', stroke: '#6e3fed', 'stroke-width': 2 }));
}

/** @param {any[]} projects @param {() => void} onMore */
function satisfaction(projects, onMore) {
  const ringHost = el('div', { id: 'nps-ring' });
  const lineHost = svg('svg', { id: 'nps-line', viewBox: '0 0 440 150', 'aria-label': 'NPS por proyecto' });
  const section = card(
    'Satisfacción del cliente',
    [
      el('div', { class: 'nps-visual' }, ringHost, el('div', {}, el('b', { class: 'account-muted', text: 'NPS por proyecto' }), lineHost)),
      el('p', { class: 'account-muted', text: 'Valores por proyecto; no hay cortes mensuales para una tendencia.' }),
    ],
    more('nps-more', onMore),
  );
  drawNps(projects.filter((p) => p.nps !== null && p.nps !== undefined), ringHost, lineHost);
  return section;
}

/** Alertas segun las horas que ya llegaron. @param {any[]} projects */
export function updateAlerts(projects) {
  const root = /** @type {HTMLElement} */ (document.getElementById('account-live-alerts'));
  const alerts = projects.filter((p) => (p.burn !== null && p.burn !== undefined && p.budget !== null && p.budget !== undefined && Number(p.burn) > Number(p.budget)) || p.late);
  const cards = alerts.map((p) => {
    const over = p.burn !== null && p.budget !== null && Number(p.burn) > Number(p.budget);
    return el('div', { class: 'account-alert' }, el('b', { text: `${p.id} · ${p.name || ''}` }), el('br'), over ? 'Consumo mayor que el presupuesto' : 'Fecha vencida');
  });
  if (!alerts.length) {
    const waiting = projects.some((p) => p.clockify_pending);
    cards.push(el('p', { class: 'account-muted', text: waiting ? 'Consultando consumos para revisar alertas...' : 'Sin alertas registradas' }));
  }
  root.replaceChildren(...cards);
}

/**
 * La rejilla de seis tarjetas; las oportunidades se agregan al final.
 * @param {any[]} projects
 * @param {{budget: () => void, nps: () => void}} actions
 * @param {Node} opportunities
 */
export function renderGrid(projects, actions, opportunities) {
  return el(
    'div',
    { class: 'account-grid' },
    models(projects),
    consumption(actions.budget),
    states(projects),
    satisfaction(projects, actions.nps),
    card('Alertas de cuenta', [el('div', { id: 'account-live-alerts' })]),
    opportunities,
  );
}
