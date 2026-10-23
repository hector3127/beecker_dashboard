// @ts-check
// La misma estructura visual, construida con nodos y texto seguro.
import { el, svg } from '#app/lib/dom.js';
import { computed, date, fmt, norm, selected } from './model.js';

const paths = {
  bars: [['path', { d: 'M4 20V11m5 9V6m5 14V9m5 11V3', 'stroke-linecap': 'round' }]],
  calendar: [['rect', { x: 4, y: 5, width: 16, height: 16, rx: 2 }], ['path', { d: 'M8 3v4m8-4v4M4 10h16' }]],
  clock: [['circle', { cx: 12, cy: 12, r: 9 }], ['path', { d: 'M12 6v6l4 2' }]],
  search: [['circle', { cx: 10, cy: 10, r: 6 }], ['path', { d: 'm15 15 5 5' }]],
  layers: [['path', { d: 'm12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5' }]],
};
/** @param {keyof typeof paths} [name] */
export function icon(name = 'bars') {
  return svg('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8 }, ...paths[name].map(([tag, attrs]) => svg(/** @type {string} */ (tag), /** @type {any} */ (attrs))));
}

/** @param {any} value @param {string} [color] */
const pill = (value, color = '') => el('span', { class: 'ci-pill ' + color, text: value || 'NA' });
/** @param {string} label @param {() => void} action @param {boolean} [active] */
const button = (label, action, active = false) => el('button', { type: 'button', class: 'ci-btn ' + (active ? 'primary' : ''), text: label, onclick: action });

/** @param {any[]} rows @param {any} data @param {any} st @param {() => void} paint */
function matrix(rows, data, st, paint) {
  const pages = Math.max(1, Math.ceil(rows.length / st.size));
  st.page = Math.min(st.page, pages);
  const headings = ['Recurso', 'Banda', 'Conceptos', 'Facturable', 'Cargabilidad', 'Capacidad Disponible', 'Tecnología', 'Delivery Manager', 'ID Proyecto', 'Proyecto', 'Inicio', 'Fin', 'Total mes'];
  const header = el('tr', {}, ...headings.map((text) => el('th', { text })), ...data.days.map((/** @type {string} */ d) => el('th', { class: 'ci-day-head' }, el('span', { text: date(d) }))));
  const body = el('tbody');
  for (const f of rows.slice((st.page - 1) * st.size, st.page * st.size)) {
    const person = el('td', {}, el('b', { text: f.recurso }));
    if (f.status) person.append(el('small', { class: 'ci-muted', text: f.status }));
    const row = el('tr', {}, person,
      el('td', {}, pill(f.banda)), el('td', {}, pill(f.concepto)),
      el('td', {}, pill(f.regla && f.regla.facturable, f.regla && f.regla.facturable === 'Facturable' ? 'green' : 'grey')),
      el('td', {}, pill(f.regla && f.regla.cargabilidad, f.regla && f.regla.cargabilidad === 'Cargable' ? 'blue' : 'grey')),
      el('td', {}, pill(f.regla && f.regla.capacidad)),
      ...['tecnologia', 'manager', 'idProyecto', 'proyecto'].map((k) => el('td', { text: f[k] || '—' })),
      el('td', { text: date(f.inicio) }), el('td', { text: date(f.fin) }), el('td', {}, el('b', { text: fmt(f.total) })));
    f.values.forEach((/** @type {number|null} */ value, /** @type {number} */ index) => {
      const person = data.people.find((/** @type {any} */ p) => norm(p.nombre).trim() === norm(f.recurso).trim());
      const color = value == null ? 'pending' : !value ? 'off' : person && person.values[index] > st.jornada + 0.001 ? 'over' : '';
      row.append(el('td', { class: 'ci-day ' + color, text: value == null ? '—' : value ? fmt(value) : '' }));
    });
    body.append(row);
  }
  const prev = button('← Anterior', () => { st.page = Math.max(1, st.page - 1); paint(); });
  const next = button('Siguiente →', () => { st.page += 1; paint(); });
  if (st.page === 1) prev.setAttribute('disabled', '');
  if (st.page === pages) next.setAttribute('disabled', '');
  return [el('div', { class: 'ci-matrix' }, el('table', { class: 'ci-table' }, el('thead', {}, header), body)),
    el('div', { class: 'ci-foot' }, el('small', { class: 'ci-muted', text: `${rows.length} asignaciones · Página ${st.page} de ${pages} · ${st.size} filas por página` }), el('div', {}, prev, ' ', next))];
}

/** @param {any} data @param {any} st */
function resources(data, st) {
  const grid = el('div', { class: 'ci-resource-grid' });
  for (const p of data.people.filter((/** @type {any} */ p) => (!st.tecnologia || p.tecnologia === st.tecnologia) && (!st.q || norm(p.nombre + ' ' + p.tecnologia).includes(norm(st.q))))) {
    const base = data.days.length * st.jornada, used = p.total;
    const free = p.values.reduce((/** @type {number} */ n, /** @type {number} */ v) => n + Math.max(0, st.jornada - v), 0);
    const over = p.values.some((/** @type {number} */ v) => v > st.jornada + 0.001);
    const fill = el('i', { class: over ? 'over' : '' });
    fill.style.width = Math.min(100, base ? used / base * 100 : 0) + '%';
    grid.append(el('div', { class: 'ci-resource' }, el('b', { text: p.nombre }),
      el('div', { class: 'ci-muted', text: (p.tecnologia || 'NA') + ' · ' + (p.banda || '') }),
      el('div', { class: 'ci-pills ci-resource-gap' }, pill(p.unknown ? 'Pendiente de datos' : over ? 'Sobre jornada' : 'Dentro de capacidad', over ? 'red' : 'green')),
      el('div', { class: 'ci-muted ci-resource-gap' }, `Registradas: ${fmt(used)} h · Base: ${fmt(base)} h`, el('br'), `Disponibles: ${p.unknown ? '—' : fmt(free) + ' h'}`),
      el('div', { class: 'ci-bar' }, fill)));
  }
  return grid;
}

/** @param {HTMLElement} box @param {any} st @param {() => void} paint */
export function render(box, st, paint) {
  if (!st.base) return;
  const data = computed(st), rows = selected(data.all, st), capacity = data.people.length * data.days.length * st.jornada;
  const pending = data.all.filter((x) => x.status).length;
  const over = data.people.filter((p) => p.values.some((/** @type {number} */ v) => v > st.jornada + 0.001)).length;
  const fact = data.all.filter((x) => x.regla && x.regla.facturable === 'Facturable').reduce((s, x) => s + x.total, 0);
  const carg = data.all.filter((x) => x.regla && x.regla.cargabilidad === 'Cargable').reduce((s, x) => s + x.total, 0);
  const stats = [['Recursos', data.people.length, 'Personas únicas del mes'], ['Capacidad base', fmt(capacity) + ' h', data.days.length + ' días × ' + st.jornada + ' h'], ['Horas facturables', fmt(fact) + ' h', 'Cargables: ' + fmt(carg) + ' h'], ['Capacidad disponible', pending ? 'Pendiente' : fmt(data.available) + ' h', pending ? 'Hay asignaciones pendientes' : 'Suma diaria por persona'], ['Sobre jornada', over, 'Más de ' + st.jornada + ' h en algún día']];
  box.replaceChildren(el('div', { class: 'ci-kpis' }, ...stats.map((s) => el('div', { class: 'ci-card ci-stat' }, el('span', { class: 'ci-icon' }, icon()), el('div', {}, el('small', { text: s[0] }), el('strong', { text: s[1] }), el('small', { text: s[2] }))))));
  if (st.base.bandasAviso) box.append(el('div', { class: 'ci-alert', text: st.base.bandasAviso }));
  if (pending) box.append(el('div', { class: 'ci-alert', text: `${pending} asignación(es) requieren completar fechas, horas o concepto. Las celdas pendientes se muestran con «—». Los totales de horas son parciales hasta resolverlas.` }));
  box.append(el('div', { class: 'ci-card' }, el('div', { class: 'ci-section-head' }, el('h3', { text: 'Asignación del mes · ' + st.mes }),
    el('div', { class: 'ci-pills' }, ...[['matrix', 'Matriz de asignaciones'], ['people', 'Capacidad por recurso']].map(([v, title]) => button(title, () => { st.view = v; st.page = 1; paint(); }, st.view === v)))),
    ...(st.view === 'matrix' ? matrix(rows, data, st, paint) : [resources(data, st)])));
  box.append(el('div', { class: 'ci-info' }, el('b', { text: 'Cálculo:' }), ' horas reales registradas en Clockify por persona, proyecto y día del mes seleccionado. No se reparten horas estimadas. La capacidad disponible suma por persona y día: máximo de 0 y (jornada − horas que afectan capacidad). Los excedentes se resaltan en rojo. Las fechas se incluyen completas y los nombres de banda/tecnología se cruzan por nombre normalizado. Fines de semana excluidos; no se descuentan festivos sin calendario. ', el('b', { text: 'Los indicadores superiores corresponden al mes completo; los filtros actúan sobre la tabla.' })));
}
