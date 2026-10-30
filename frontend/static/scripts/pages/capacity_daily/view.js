// @ts-check
// Capacidad del equipo: indicadores, matriz persona x proyecto y vista por persona.
import { el, svg } from '#app/lib/dom.js';
import { date, fmt, indicators, isWeekend, selectedPeople, selectedRows } from './model.js';
import { renderResourceDetail } from './resource_detail.js';

const paths = {
  bars: [['path', { d: 'M4 20V11m5 9V6m5 14V9m5 11V3', 'stroke-linecap': 'round' }]],
  calendar: [['rect', { x: 4, y: 5, width: 16, height: 16, rx: 2 }], ['path', { d: 'M8 3v4m8-4v4M4 10h16' }]],
  clock: [['circle', { cx: 12, cy: 12, r: 9 }], ['path', { d: 'M12 6v6l4 2' }]],
  search: [['circle', { cx: 10, cy: 10, r: 6 }], ['path', { d: 'm15 15 5 5' }]],
  layers: [['path', { d: 'm12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5' }]],
};
/** @param {keyof typeof paths} [name] */
export function icon(name = 'bars') {
  return svg('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8 },
    ...paths[name].map(([tag, attrs]) => svg(/** @type {string} */ (tag), /** @type {any} */ (attrs))));
}

/** @param {any} value @param {string} [color] */
const pill = (value, color = '') => el('span', { class: 'ci-pill ' + color, text: value || 'NA' });
/** @param {string} label @param {() => void} action @param {boolean} [active] */
const button = (label, action, active = false) =>
  el('button', { type: 'button', class: 'ci-btn ' + (active ? 'primary' : ''), text: label, onclick: action });

/** @param {string} name @param {any} st @param {() => void} paint */
function personButton(name, st, paint) {
  return el('button', { type: 'button', class: 'ci-person-link', 'data-resource-name': name, text: name,
    'aria-label': 'Ver horas diarias de ' + name,
    onclick: () => {
      st.detailResource = name;
      paint();
      document.getElementById('ci-person-heading')?.focus();
    } });
}

/** @param {any} data @param {any} st @param {() => void} paint */
function matrix(data, st, paint) {
  const rows = selectedRows(data, st);
  const pages = Math.max(1, Math.ceil(rows.length / st.size));
  st.page = Math.min(st.page, pages);
  const limit = data.diasHabiles * st.jornada;
  const total = new Map(data.personas.map((/** @type {any} */ p) => [p.nombre, p.total]));
  const headings = ['Recurso', 'ID Clockify', 'Rol', 'Banda', 'Delivery Manager', 'ID Proyecto', 'Proyecto', 'Facturables', 'No facturables', 'Total mes'];
  const header = el('tr', {}, ...headings.map((text) => el('th', { text })),
    ...data.dias.map((/** @type {string} */ d) => el('th', { class: 'ci-day-head' + (isWeekend(d) ? ' weekend' : ''), text: date(d) })));
  const body = el('tbody');
  for (const r of rows.slice((st.page - 1) * st.size, st.page * st.size)) {
    const over = total.get(r.nombre) > limit;
    body.append(el('tr', {},
      el('td', {}, personButton(r.nombre, st, paint)),
      el('td', { text: r.clockifyId || '—' }),
      el('td', {}, pill(r.rol)), el('td', {}, pill(r.banda)),
      el('td', { text: r.idProyecto ? r.dm || 'Sin Delivery Manager confirmado' : '—' }),
      el('td', { text: r.idProyecto || '—' }),
      el('td', { text: r.proyecto || (r.idProyecto ? '—' : 'Sin registros en el mes') }),
      el('td', { text: fmt(r.facturables) }), el('td', { text: fmt(r.noFacturables) }),
      el('td', {}, el('b', { text: fmt(r.total) })),
      ...data.dias.map((/** @type {string} */ d) => {
        const value = r.daily[d];
        return el('td', { class: 'ci-day ' + (!value ? 'off' : over && value > st.jornada + 0.001 ? 'over' : '') + (isWeekend(d) ? ' weekend' : ''), text: value ? fmt(value) : '' });
      })));
  }
  const prev = button('← Anterior', () => { st.page = Math.max(1, st.page - 1); paint(); });
  const next = button('Siguiente →', () => { st.page += 1; paint(); });
  if (st.page === 1) prev.setAttribute('disabled', '');
  if (st.page === pages) next.setAttribute('disabled', '');
  return [
    el('div', { class: 'ci-matrix' }, el('table', { class: 'ci-table' }, el('thead', {}, header), body)),
    el('div', { class: 'ci-foot' },
      el('small', { class: 'ci-muted', text: `${rows.length} filas · Página ${st.page} de ${pages} · ${st.size} filas por página` }),
      el('div', {}, prev, ' ', next)),
  ];
}

/** @param {any} data @param {any} st @param {() => void} paint */
function people(data, st, paint) {
  const grid = el('div', { class: 'ci-resource-grid' });
  const limit = data.diasHabiles * st.jornada;
  for (const p of selectedPeople(data, st)) {
    const over = p.total > limit;
    const fill = el('i', { class: over ? 'over' : '' });
    fill.style.width = Math.min(100, limit ? (p.total / limit) * 100 : 0) + '%';
    grid.append(el('div', { class: 'ci-resource' }, personButton(p.nombre, st, paint),
      el('div', { class: 'ci-muted', text: `${p.rol} · ${p.banda}` }),
      el('div', { class: 'ci-pills ci-resource-gap' }, pill(over ? 'Sobre jornada' : p.total ? 'Dentro de capacidad' : 'Sin registros', over ? 'red' : 'green')),
      el('div', { class: 'ci-muted ci-resource-gap' },
        `Registradas: ${fmt(p.total)} h · Base: ${fmt(limit)} h`, el('br'),
        `Disponibles: ${fmt(limit - p.total)} h`),
      el('div', { class: 'ci-bar' }, fill)));
  }
  return grid;
}

/** @param {HTMLElement} box @param {any} st @param {() => void} paint */
export function render(box, st, paint) {
  const data = st.data;
  if (!data) return;
  const ind = indicators(data, st.jornada);
  const stats = [
    ['Personas vigentes', ind.people, `${ind.withHours} con horas registradas`],
    ['Capacidad base', fmt(ind.base) + ' h', `${ind.people} personas × ${data.diasHabiles} días × ${st.jornada} h`],
    ['Horas registradas', fmt(ind.registered) + ' h', `${fmt(ind.billable)} h facturables`],
    ['Saldo disponible', fmt(ind.balance) + ' h', ind.balance < 0 ? 'Se superó la capacidad' : 'Capacidad base − horas registradas'],
    ['Utilización', ind.utilization == null ? '—' : fmt(ind.utilization) + '%', `${ind.over} persona(s) sobre jornada`],
  ];
  box.replaceChildren(el('div', { class: 'ci-kpis' }, ...stats.map((s) => el('div', { class: 'ci-card ci-stat' },
    el('span', { class: 'ci-icon' }, icon()), el('div', {}, el('small', { text: s[0] }), el('strong', { text: String(s[1]) }), el('small', { class: 'ci-muted', text: s[2] }))))));
  box.append(el('div', { class: 'ci-card' },
    el('div', { class: 'ci-section-head' }, el('h3', { text: 'Horas del mes · ' + st.mes }),
      el('div', { class: 'ci-pills' }, ...[['matrix', 'Matriz por proyecto'], ['people', 'Capacidad por recurso']]
        .map(([v, title]) => button(title, () => { st.view = v; st.page = 1; paint(); }, st.view === v)))),
    ...(st.view === 'matrix' ? matrix(data, st, paint) : [people(data, st, paint)])));
  if (st.detailResource) {
    const section = renderResourceDetail(data, st.detailResource, () => {
      const name = st.detailResource;
      st.detailResource = '';
      paint();
      [...box.querySelectorAll('[data-resource-name]')].find((node) => node.getAttribute('data-resource-name') === name)?.focus();
    });
    box.lastElementChild?.replaceWith(section);
  }
  box.append(el('div', { class: 'ci-info' }, el('b', { text: 'Cálculo:' }),
    ' personas de Bandas/rol con rol Dev, QA, ROC, Arq, BA o SM y banda vigente en el mes (sin banda, Baja ni NA). Horas: todo Clockify de esas personas, facturable o no y también en fines de semana, excepto Comida. Capacidad base = personas × días hábiles (sin festivos de México) × jornada. Delivery Manager y nombre del proyecto salen del inventario Summary, con respaldo de MPB, Proyectos e Histórico.'));
}
