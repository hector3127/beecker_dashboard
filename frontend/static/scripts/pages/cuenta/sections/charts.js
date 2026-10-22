// @ts-check
// Graficas de la cuenta: avance por modelo, horas por servicio, estados y NPS.
import { el, svg } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { DONUT, donutArcs } from '#app/lib/charts.js';
import { byService, npsAverage, npsProjects, stateCounts } from '#app/lib/account-metrics.js';

const hours = (/** @type {number} */ value) => `${formatNumber(value, 1)} h`;

/** @param {string} title @param {...(Node|string)} body */
const panel = (title, ...body) => el('section', { class: 'card cuenta-panel' }, el('h2', { text: title }), ...body);

/** Porcentaje de cada modelo: completados, otras etapas y con alertas. */
function modelProgress(/** @type {ReturnType<typeof byService>} */ groups) {
  const part = (/** @type {string} */ kind, /** @type {number} */ value) =>
    el('i', { class: `seg ${kind}`, style: { width: `${value}%` }, text: value > 10 ? `${value}%` : '' });
  return panel(
    'Avance de proyectos por modelo de servicio',
    ...groups.map((g) =>
      el(
        'div',
        { class: 'model-row' },
        el('span', { text: g.name }),
        el('div', { class: 'model-track' }, part('done', g.completed), part('other', g.other), part('risk', g.risk)),
        el('b', { text: String(g.count) }),
      ),
    ),
    el('p', { class: 'note', text: '● Completados · ● Otras etapas · ● Con alertas' }),
  );
}

/** Presupuesto contra consumo por servicio, con la barra mas alta como escala. */
function serviceHours(/** @type {ReturnType<typeof byService>} */ groups) {
  const scale = Math.max(1, ...groups.flatMap((g) => [g.budget, g.burn]));
  const bar = (/** @type {string} */ kind, /** @type {number} */ value) =>
    el('i', { class: `bar ${kind}`, style: { height: `${(value / scale) * 100}%` }, title: `${kind === 'budget' ? 'Presupuesto' : 'Consumo'} ${hours(value)}` });
  return panel(
    'Consumo de horas vs. presupuesto',
    el(
      'div',
      { class: 'service-chart' },
      ...groups.map((g) =>
        el(
          'div',
          { class: 'service-column' },
          el('div', { class: 'service-bars' }, bar('budget', g.budget), bar('burn', g.burn)),
          el('span', { class: g.budget && g.burn > g.budget ? 'bad' : 'good', text: `${g.name} · ${g.budget ? `${Math.round((g.burn / g.budget) * 100)}%` : 'NA'}` }),
        ),
      ),
    ),
    el('p', { class: 'note', text: 'Por servicio · acumulado de los proyectos' }),
  );
}

/** @param {import('#app/lib/account-metrics.js').AccountProject[]} projects */
function stateDonut(projects) {
  const states = stateCounts(projects);
  const arcs = donutArcs(states.map((s) => s.count));
  return panel(
    'Proyectos por estado',
    el(
      'div',
      { class: 'state-chart' },
      svg(
        'svg',
        { viewBox: '0 0 160 160', role: 'img', 'aria-label': 'Distribución de proyectos por estado' },
        svg(
          'g',
          { fill: 'none', 'stroke-width': 18, transform: 'rotate(-90 80 80)' },
          ...arcs.map((arc, index) =>
            svg('circle', { class: `slice c${index % 5}`, cx: 80, cy: 80, r: DONUT.radius * 0.95, 'stroke-dasharray': `${arc.dash * 0.95} ${arc.gap * 0.95 + arc.dash * 0.05}`, 'stroke-dashoffset': arc.offset * 0.95 }),
          ),
        ),
        svg('text', { class: 'donut-value', x: 80, y: 82, 'text-anchor': 'middle' }, String(projects.length)),
        svg('text', { class: 'donut-caption', x: 80, y: 98, 'text-anchor': 'middle' }, 'proyectos'),
      ),
      el(
        'div',
        {},
        ...states.map((s, index) => el('p', {}, el('i', { class: `dot c${index % 5}` }), `${s.name} `, el('b', { text: `${s.count} (${s.percent}%)` }))),
      ),
    ),
  );
}

/** NPS por proyecto: promedio y puntos de los primeros seis. */
function satisfaction(/** @type {import('#app/lib/account-metrics.js').AccountProject[]} */ projects) {
  const rated = npsProjects(projects);
  const average = npsAverage(projects);
  const first = rated.slice(0, 6);
  const x = (/** @type {number} */ i) => 35 + (i * 375) / Math.max(1, first.length - 1);
  const y = (/** @type {number} */ value) => 115 - Math.max(0, Math.min(100, value));
  const line = svg('svg', { viewBox: '0 0 440 150', role: 'img', 'aria-label': 'NPS por proyecto' });
  for (const mark of [0, 25, 50, 75, 100]) {
    line.append(svg('line', { class: 'grid', x1: 24, x2: 425, y1: y(mark), y2: y(mark) }), svg('text', { class: 'axis', x: 20, y: y(mark) + 3, 'text-anchor': 'end' }, String(mark)));
  }
  line.append(svg('polyline', { class: 'nps-line', fill: 'none', points: first.map((p, i) => `${x(i)},${y(Number(p.nps))}`).join(' ') }));
  first.forEach((p, i) => line.append(svg('circle', { class: 'nps-dot', cx: x(i), cy: y(Number(p.nps)), r: 3 }), svg('text', { class: 'axis', x: x(i), y: 137, 'text-anchor': 'middle' }, p.id)));
  return panel(
    'Satisfacción del cliente',
    rated.length
      ? el(
          'div',
          { class: 'nps-visual' },
          el('div', { class: 'nps-average' }, el('strong', { text: String(Math.round(/** @type {number} */ (average))) }), el('small', { text: 'NPS promedio' })),
          el('div', {}, el('b', { class: 'note', text: 'NPS por proyecto' }), line),
        )
      : el('p', { class: 'note', text: 'Sin NPS registrado en esta cuenta.' }),
    el('p', { class: 'note', text: 'Valores por proyecto; no hay cortes mensuales para una tendencia.' }),
  );
}

/**
 * @param {HTMLElement} container
 * @param {import('#app/lib/account-metrics.js').AccountProject[]} projects
 */
export function renderCharts(container, projects) {
  const groups = byService(projects);
  container.append(modelProgress(groups), serviceHours(groups), stateDonut(projects), satisfaction(projects));
}
