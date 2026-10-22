// @ts-check
// Ventanas «Ver más» de la cuenta: backlog, procesos ROC, NPS y presupuesto.
import { el, svg } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { budgetView, npsProjects, pageOf } from '#app/lib/account-metrics.js';
import { openDetail } from '#app/ui/detail-dialog.js';
import { filteredTable } from '#app/ui/filtered-table.js';

/** @param {number} value */
const hours = (value) => `${formatNumber(Number(value || 0), 1)} h`;
const text = (/** @type {unknown} */ value) => (value == null ? '' : String(value));

/** @param {any[]} items */
export function openBacklog(items) {
  const body = openDetail('Backlog de la cuenta', { wide: true });
  filteredTable(body, {
    headers: ['Account Name', 'Opportunity Name', 'Delivery Manager', 'Opportunity Stage', 'Fecha de cierre', 'Total Hours'],
    rows: items.map((o) => [text(o.account), text(o.name), text(o.manager), text(o.stage), text(o.close), hours(o.hours)]),
    filterColumn: 3,
    placeholder: 'Buscar cuenta o proyecto…',
  });
}

/** @param {any[]} items */
export function openRoc(items) {
  const body = openDetail('Procesos de la cuenta en ROC', { wide: true });
  filteredTable(body, {
    headers: ['Proceso', 'ID', 'Servicio', 'BOT ID', 'Estado'],
    rows: items.map((p) => [text(p.process), text(p.id), text(p.service), text(p.bot_id), text(p.state)]),
    filterColumn: 4,
    placeholder: 'Buscar proceso o BOT…',
  });
}

/** NPS de todos los proyectos; la grafica se desliza si no caben los IDs. @param {import('#app/lib/account-metrics.js').AccountProject[]} projects */
export function openNps(projects) {
  const rated = npsProjects(projects);
  const body = openDetail('Satisfacción del cliente · NPS por proyecto', { wide: true });
  const width = Math.max(1050, rated.length * 120);
  const y = (/** @type {number} */ value) => 210 - Math.max(0, Math.min(100, value)) * 1.5;
  const chart = svg('svg', { viewBox: `0 0 ${width} 270`, width, height: 270, role: 'img', 'aria-label': 'NPS por proyecto' });
  for (const mark of [0, 25, 50, 75, 100]) {
    chart.append(svg('line', { class: 'grid', x1: 28, x2: width - 20, y1: y(mark), y2: y(mark) }), svg('text', { class: 'axis-big', x: 22, y: y(mark) + 3, 'text-anchor': 'end' }, String(mark)));
  }
  chart.append(svg('polyline', { class: 'nps-line', fill: 'none', points: rated.map((p, i) => `${40 + i * 120},${y(Number(p.nps))}`).join(' ') }));
  rated.forEach((p, i) => {
    const dot = svg('circle', { class: 'nps-dot', cx: 40 + i * 120, cy: y(Number(p.nps)), r: 4 }, svg('title', {}, `${p.id} · ${p.name}: ${p.nps} NPS`));
    chart.append(dot, svg('text', { class: 'axis-big', x: 40 + i * 120, y: 240, 'text-anchor': 'middle' }, p.id));
  });
  body.append(
    el('p', { class: 'note', text: 'Todos los proyectos con NPS registrado; desliza horizontalmente para ver los IDs completos.' }),
    el('div', { class: 'detail-scroll' }, chart),
    el('p', { class: 'note', text: 'Comparación entre proyectos; no es una tendencia mensual.' }),
  );
}

/** @param {number} percent @param {boolean} over */
const ratioPill = (percent, over) => el('span', { class: `ratio${over ? ' over' : ''}`, text: Number.isFinite(percent) ? `${Math.round(percent)}%` : 'NA' });

/**
 * Presupuesto contra consumo, por servicio o por proyecto.
 * @param {import('#app/lib/account-metrics.js').AccountProject[]} projects
 */
export function openBudget(projects) {
  const body = openDetail('Presupuesto vs consumo', { wide: true });
  const services = [...new Set(budgetView(projects).services.map((s) => s.name))];
  const state = { service: '', by: /** @type {'service' | 'project'} */ ('service'), search: '', page: 1 };
  const grouping = /** @type {HTMLSelectElement} */ (
    el('select', { 'aria-label': 'Agrupar por' }, el('option', { value: 'service', text: 'Servicio' }), el('option', { value: 'project', text: 'Proyecto' }))
  );
  const search = /** @type {HTMLInputElement} */ (el('input', { type: 'search', placeholder: 'Buscar proyecto…', 'aria-label': 'Buscar proyecto' }));
  const tabs = el('div', { class: 'service-tabs' }, el('b', { text: 'Servicio' }));
  const output = el('div');
  for (const name of ['', ...services]) {
    const button = el('button', {
      type: 'button',
      class: 'tab',
      'aria-pressed': String(name === state.service),
      text: name || 'Todos',
      onclick: () => {
        state.service = name;
        state.page = 1;
        tabs.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b === button)));
        draw();
      },
    });
    tabs.append(button);
  }
  body.append(el('p', { class: 'note', text: 'Comparación de horas por proyecto y por servicio.' }), el('div', { class: 'detail-controls' }, tabs, grouping, search), output);

  function draw() {
    const view = budgetView(projects, state);
    const { totals } = view;
    const scale = Math.max(1, ...view.groups.flatMap((g) => [g.budget, g.burn]));
    const metric = (/** @type {string} */ label, /** @type {string} */ value) => el('div', { class: 'metric' }, el('small', { text: label }), el('strong', { text: value }));
    const rows = view.groups.map((g) => {
      const track = (/** @type {'budget' | 'burn'} */ key) =>
        el('div', { class: 'comparison-track' }, el('i', { class: `detail-bar ${key}`, style: { width: `${(g[key] / scale) * 100}%` }, title: hours(g[key]) }), el('small', { text: hours(g[key]) }));
      return el('div', { class: 'comparison-row' }, el('b', { text: g.name }), el('div', {}, track('budget'), track('burn')), ratioPill(g.budget ? (g.burn / g.budget) * 100 : NaN, g.budget > 0 && g.burn > g.budget));
    });
    const share = [...view.services].sort((a, b) => b.burn - a.burn).slice(0, 3);
    const reading = el(
      'div',
      { class: 'reading' },
      el('h3', { text: 'Lectura rápida' }),
      el('p', { text: `${view.exceeded} de ${view.selected.length} proyectos exceden sus horas presupuestadas.` }),
      ...share.map((s) => el('p', { text: `${s.name} concentra ${Math.round(s.percent)}% del consumo y registra ${s.budget ? `${Math.round((s.burn / s.budget) * 100)}% frente a presupuesto` : 'sin presupuesto comparable'}.` })),
    );
    const detail = pageOf(view.selected, state.page, 6);
    state.page = detail.page;
    const pager = el('div', { class: 'detail-pager' }, el('span', { text: `Mostrando ${detail.from}–${detail.to} de ${view.selected.length} proyectos` }));
    const buttons = el('div');
    const step = (/** @type {string} */ label, /** @type {number} */ page, /** @type {boolean} */ off, /** @type {boolean} */ current = false) =>
      el('button', { type: 'button', class: 'btn btn-ghost', 'aria-current': current ? 'page' : false, disabled: off, text: label, onclick: () => ((state.page = page), draw()) });
    buttons.append(step('‹', detail.page - 1, detail.page === 1));
    for (let n = 1; n <= detail.pages; n++) buttons.append(step(String(n), n, false, n === detail.page));
    buttons.append(step('›', detail.page + 1, detail.page === detail.pages));
    pager.append(buttons);
    output.replaceChildren(
      el('div', { class: 'detail-metrics' }, metric('Presupuesto total', hours(totals.budget)), metric('Consumo total', hours(totals.burn)), metric('% de consumo', totals.budget ? `${Math.round((totals.burn / totals.budget) * 100)}%` : 'NA'), metric('Proyectos excedidos', `${view.exceeded} de ${view.selected.length}`)),
      el('div', { class: 'detail-charts' }, el('div', {}, el('h3', { text: `Comparativo por ${state.by === 'service' ? 'servicio' : 'proyecto'}` }), ...rows), el('div', {}, el('h3', { text: 'Distribución del consumo por servicio' }), ...view.services.map((s) => el('p', { text: `${s.name}: ${hours(s.burn)} · ${Math.round(s.percent)}%` })), reading)),
      el(
        'section',
        { class: 'budget-project-card' },
        el('h3', { text: 'Detalle por proyecto' }),
        el(
          'div',
          { class: 'detail-scroll' },
          el(
            'table',
            {},
            el('thead', {}, el('tr', {}, ...['Proyecto', 'Servicio', 'Presupuesto', 'Consumo', 'Variación', 'Estado'].map((h) => el('th', { scope: 'col', text: h })))),
            el(
              'tbody',
              {},
              ...detail.items.map((p) => {
                const over = Number(p.budget) > 0 && Number(p.burn) > Number(p.budget);
                const variation = Number(p.budget) > 0 ? `${over ? '+' : ''}${Math.round(((Number(p.burn) - Number(p.budget)) / Number(p.budget)) * 100)}%` : 'NA';
                return el('tr', {}, el('td', { text: `${p.id} · ${p.name}` }), el('td', { text: p.service || 'Sin servicio' }), el('td', { text: p.budget == null ? 'Sin datos' : hours(p.budget) }), el('td', { text: hours(Number(p.burn)) }), el('td', { class: over ? 'bad' : 'good', text: variation }), el('td', {}, el('span', { class: over ? 'status over' : 'status ok', text: over ? 'Excedido' : 'En control' })));
              }),
            ),
          ),
        ),
        pager,
      ),
    );
  }

  grouping.addEventListener('change', () => ((state.by = /** @type {'service' | 'project'} */ (grouping.value)), (state.page = 1), draw()));
  search.addEventListener('input', () => ((state.search = search.value), (state.page = 1), draw()));
  draw();
}
