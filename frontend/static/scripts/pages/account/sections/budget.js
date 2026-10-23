// @ts-check
// «Presupuesto vs consumo»: comparativo por servicio o proyecto, reparto del
// consumo y detalle por proyecto con paginas.
import { serviceName } from '#app/lib/account-summary.js';
import { element, hours, shape } from './modal.js';

const NS = 'http://www.w3.org/2000/svg';
const METRIC_PATHS = ['M12 6v12M9 9h4l-2 6h4', 'M8 15v-3M12 15V8M16 15v-6', 'M12 6v6l4 2', 'M12 7v6M12 16h.01'];
const DISTRIBUTION_COLORS = ['#6336ea', '#4289ed', '#a782f7', '#f7ad32'];

/** @param {number} value @param {number} total */
const ratio = (value, total) => (total ? `${Math.round((value / total) * 100)}%` : 'NA');

/** @param {any[]} selected @param {HTMLElement} output */
function drawMetrics(selected, output) {
  const budget = selected.reduce((n, p) => n + Number(p.budget || 0), 0);
  const burn = selected.reduce((n, p) => n + Number(p.burn || 0), 0);
  const exceeded = selected.filter((p) => p.budget > 0 && p.burn !== null && p.burn > p.budget).length;
  const metrics = element('div', null, output, 'detail-metrics');
  const cards = [
    ['Presupuesto total', hours(budget)],
    ['Consumo total', hours(burn)],
    ['% de consumo', budget ? `${Math.round((burn / budget) * 100)}%` : 'NA'],
    ['Proyectos excedidos', `${exceeded} de ${selected.length}`],
  ];
  cards.forEach(([label, value], index) => {
    const card = element('div', null, metrics);
    const icon = element('span', null, card, 'detail-metric-icon');
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    icon.append(svg);
    shape(svg, 'circle', { cx: 12, cy: 12, r: 8, fill: 'none', stroke: 'currentColor', 'stroke-width': 2 });
    shape(svg, 'path', { d: METRIC_PATHS[index], fill: 'none', stroke: 'currentColor', 'stroke-width': 2 });
    element('small', label, card);
    element('strong', value, card);
    const track = element('div', null, card, 'metric-progress');
    const bar = element('i', null, track);
    const fill = index === 0 ? 100 : index < 3 ? (budget ? (burn / budget) * 100 : 0) : selected.length ? (exceeded / selected.length) * 100 : 0;
    bar.style.width = `${Math.min(100, fill)}%`;
    element('small', index === 3 ? '% de proyectos' : index === 2 ? 'vs. 100%' : 'del presupuesto', card);
  });
  return { budget, burn, exceeded };
}

/**
 * @param {any[]} selected
 * @param {string} grouping 'service' o 'project'
 * @param {HTMLElement} output
 * @param {{burn: number, exceeded: number}} totals
 */
function drawCharts(selected, grouping, output, totals) {
  const { burn, exceeded } = totals;
  const chart = element('div', null, output, 'detail-charts');
  const bars = element('div', null, chart);
  const distribution = element('div', null, chart);
  element('h3', `Comparativo por ${grouping === 'service' ? 'servicio' : 'proyecto'}`, bars);
  element('h3', 'Distribución del consumo por servicio', distribution);
  /** @type {Map<string, {budget: number, burn: number}>} */
  const unsorted = new Map();
  for (const p of selected) {
    const key = grouping === 'service' ? serviceName(p) : p.id;
    const group = unsorted.get(key) || { budget: 0, burn: 0 };
    group.budget += Number(p.budget || 0);
    group.burn += Number(p.burn || 0);
    unsorted.set(key, group);
  }
  const groups = new Map([...unsorted.entries()].sort((a, b) => a[0].localeCompare(b[0], 'es')));
  const maximum = Math.max(1, ...[...groups.values()].flatMap((g) => [g.budget, g.burn]));
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 120 120');
  distribution.append(svg);
  shape(svg, 'circle', { cx: 60, cy: 60, r: 42, fill: 'none', stroke: '#eee8fa', 'stroke-width': 14 });
  let offset = 0;
  groups.forEach((g, name) => {
    const row = element('div', null, bars, 'comparison-row');
    element('b', name, row);
    const pairs = element('div', null, row);
    const share = element('span', ratio(g.burn, g.budget), row, 'comparison-ratio');
    share.classList.toggle('over', g.budget > 0 && g.burn > g.budget);
    for (const [key, color] of /** @type {const} */ ([['budget', '#cdbbfd'], ['burn', '#6436eb']])) {
      const track = element('div', null, pairs, 'comparison-track');
      const bar = element('i', null, track, 'detail-bar');
      bar.style.width = `${(g[key] / maximum) * 100}%`;
      bar.style.background = color;
      bar.title = hours(g[key]);
      element('small', hours(g[key]), track);
    }
    const percent = burn ? (g.burn / burn) * 100 : 0;
    const color = DISTRIBUTION_COLORS[[...groups.keys()].indexOf(name) % DISTRIBUTION_COLORS.length];
    shape(svg, 'circle', { cx: 60, cy: 60, r: 42, pathLength: 100, fill: 'none', stroke: color, 'stroke-width': 14, 'stroke-dasharray': `${percent} 100`, 'stroke-dashoffset': -offset, transform: 'rotate(-90 60 60)' });
    offset += percent;
    element('p', `${name}: ${hours(g.burn)} · ${Math.round(percent)}%`, distribution);
  });
  const centre = burn >= 1000 ? `${(burn / 1000).toLocaleString('es-MX', { maximumFractionDigits: 1 })} mil` : Number(burn).toLocaleString('es-MX');
  shape(svg, 'text', { x: 60, y: 60, 'text-anchor': 'middle', 'font-size': 12, 'font-weight': 800, fill: '#211447' }, centre);
  shape(svg, 'text', { x: 60, y: 76, 'text-anchor': 'middle', 'font-size': 8, fill: '#9384ab' }, 'horas');
  const left = element('div', null, null, 'distribution-left');
  [...distribution.children].forEach((child) => left.append(child));
  distribution.append(left);
  const insights = element('div', null, distribution, 'reading');
  element('h3', 'Lectura rápida', insights);
  element('p', `${exceeded} de ${selected.length} proyectos exceden sus horas presupuestadas.`, insights);
  [...groups.entries()]
    .sort((a, b) => b[1].burn - a[1].burn)
    .slice(0, 3)
    .forEach(([name, g]) => {
      const against = g.budget ? `${Math.round((g.burn / g.budget) * 100)}% frente a presupuesto` : 'sin presupuesto comparable';
      element('p', `${name} concentra ${burn ? Math.round((g.burn / burn) * 100) : 0}% del consumo y registra ${against}.`, insights);
    });
}

/**
 * @param {any[]} selected
 * @param {HTMLElement} output
 * @param {HTMLInputElement} search
 * @param {{page: number}} state
 * @param {() => void} redraw
 */
function drawProjects(selected, output, search, state, redraw) {
  const card = element('section', null, output, 'budget-project-card');
  element('h3', 'Detalle por proyecto', card);
  card.append(search);
  const table = element('table', null, card);
  const head = element('tr', null, table);
  ['Proyecto', 'Servicio', 'Presupuesto', 'Consumo', 'Variación', 'Estado'].forEach((label) => element('th', label, head));
  const pages = Math.max(1, Math.ceil(selected.length / 6));
  state.page = Math.min(state.page, pages);
  selected.slice((state.page - 1) * 6, state.page * 6).forEach((p) => {
    const tr = element('tr', null, table);
    const over = p.budget > 0 && p.burn > p.budget;
    const cells = [
      `${p.id} · ${p.name}`,
      serviceName(p),
      p.budget === null || p.budget === undefined ? 'Sin datos' : hours(p.budget),
      p.clockify_pending ? 'Consultando…' : p.burn === null || p.burn === undefined ? 'Sin datos' : hours(p.burn),
      p.budget > 0 && p.burn !== null && p.burn !== undefined ? `${p.burn > p.budget ? '+' : ''}${Math.round(((p.burn - p.budget) / p.budget) * 100)}%` : 'NA',
      p.clockify_pending ? 'Pendiente' : over ? 'Excedido' : 'En control',
    ];
    cells.forEach((value) => element('td', value, tr));
    const stateCell = /** @type {HTMLElement} */ (tr.lastChild);
    stateCell.style.color = over ? '#ed3864' : '#00a470';
    stateCell.replaceChildren(element('span', stateCell.textContent, null, over ? 'detail-over' : 'detail-controlled'));
    const variation = /** @type {HTMLElement} */ (tr.children[4]);
    variation.style.color = over ? '#ed3864' : '#00a470';
    const track = element('span', null, null, 'table-consumption');
    const bar = element('i', null, track);
    bar.style.width = `${Math.min(100, p.budget > 0 ? (p.burn / p.budget) * 100 : 0)}%`;
    bar.style.background = over ? '#ef5273' : '#6132ee';
    /** @type {HTMLElement} */ (tr.children[3]).prepend(track);
  });
  const pager = element('div', null, card, 'detail-pager');
  element('span', `Mostrando ${selected.length ? (state.page - 1) * 6 + 1 : 0}–${Math.min(state.page * 6, selected.length)} de ${selected.length} proyectos`, pager);
  const buttons = element('div', null, pager);
  const prev = /** @type {HTMLButtonElement} */ (element('button', '‹', buttons));
  prev.disabled = state.page === 1;
  prev.onclick = () => {
    state.page -= 1;
    redraw();
  };
  for (let n = 1; n <= pages; n++) {
    const button = element('button', n, buttons);
    button.classList.toggle('selected', n === state.page);
    button.onclick = () => {
      state.page = n;
      redraw();
    };
  }
  const next = /** @type {HTMLButtonElement} */ (element('button', '›', buttons));
  next.disabled = state.page === pages;
  next.onclick = () => {
    state.page += 1;
    redraw();
  };
}

/**
 * @param {ReturnType<typeof import('./modal.js').createModal>} detail
 * @param {any[]} projects
 */
export function openBudget(detail, projects) {
  const root = detail.start('Presupuesto vs consumo');
  detail.modal.classList.add('budget-layout');
  element('p', 'Comparación de horas por proyecto y por servicio.', root, 'account-muted');
  const controls = element('div', null, root, 'detail-controls');
  const service = /** @type {HTMLSelectElement} */ (element('select', null, controls));
  const grouping = /** @type {HTMLSelectElement} */ (element('select', null, controls));
  const search = /** @type {HTMLInputElement} */ (element('input', null, controls));
  /** @type {HTMLOptionElement} */ (element('option', 'Todos los servicios', service)).value = '';
  const names = [...new Set(projects.map(serviceName))];
  names.forEach((name) => element('option', name, service));
  /** @type {HTMLOptionElement} */ (element('option', 'Servicio', grouping)).value = 'service';
  /** @type {HTMLOptionElement} */ (element('option', 'Proyecto', grouping)).value = 'project';
  search.placeholder = 'Buscar proyecto…';
  service.style.display = 'none';
  const tabs = element('div', null, controls, 'service-tabs');
  element('b', 'Servicio', tabs);
  const state = { page: 1 };
  for (const name of ['', ...[...names].sort()]) {
    const button = /** @type {HTMLButtonElement} */ (element('button', name || 'Todos', tabs));
    button.type = 'button';
    button.onclick = () => {
      service.value = name;
      tabs.querySelectorAll('button').forEach((b) => b.classList.toggle('selected', b === button));
      state.page = 1;
      draw();
    };
    if (!name) button.classList.add('selected');
  }
  const output = element('div', null, root);

  function draw() {
    output.replaceChildren();
    const wanted = search.value.toLowerCase();
    const selected = projects.filter(
      (p) => !p.clockify_pending && !p.clockify_error && p.burn !== null && p.burn !== undefined && (!service.value || serviceName(p) === service.value) && `${p.id} ${p.name}`.toLowerCase().includes(wanted),
    );
    const totals = drawMetrics(selected, output);
    drawCharts(selected, grouping.value, output, totals);
    drawProjects(selected, output, search, state, draw);
  }
  service.onchange = grouping.onchange = search.oninput = () => {
    state.page = 1;
    draw();
  };
  draw();
}
