// @ts-check
import { el, svg } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
const hours = (value) => formatNumber(value, 2) + ' h';
const normal = (value) => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const folder = () => svg('svg', { viewBox: '0 0 24 24', width: 18, height: 18, fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8, 'aria-hidden': 'true' }, svg('path', { d: 'M3 7V4h6l3 3h9v13H3Z' }));
const button = (text, action, props = {}) => el('button', { type: 'button', class: 'inv-detail-button', text, onclick: action, ...props });

export function mountResourceDetail() {
  const source = document.getElementById('investment-people-data');
  const panel = document.getElementById('inv-resource-detail');
  const card = document.querySelector('.inv-resources');
  if (!source || !panel || !card) return;
  const people = JSON.parse(source.textContent || '[]');
  let active = -1, query = '', sort = 'total', descending = true, page = 1, size = 5;
  let opener = null;
  const options = () => people[active].projects.filter((p) => normal(p.name).includes(normal(query))).slice().sort((a, b) => {
    const value = sort === 'name' ? a.name.localeCompare(b.name, 'es') : a[sort] - b[sort];
    return (descending ? -1 : 1) * value || a.name.localeCompare(b.name, 'es');
  });
  const close = () => {
    panel.hidden = true;
    panel.replaceChildren();
    card.classList.remove('is-open');
    document.querySelectorAll('[data-investment-person]').forEach((node) => node.setAttribute('aria-pressed', 'false'));
    document.querySelectorAll('[data-investment-person-row]').forEach((node) => node.classList.remove('selected'));
    opener?.focus({ preventScroll: true });
    active = -1;
  };
  const download = () => {
    const person = people[active];
    const safe = (value) => {
      let text = String(value);
      if (/^[=+@-]/.test(text)) text = "'" + text;
      return '"' + text.replace(/"/g, '""') + '"';
    };
    const rows = [['Recurso', 'Especialidad', 'Proyecto', 'Comercial (h)', 'Operativa (h)', 'Total (h)'],
      ...options().map((row) => [person.name, person.area, row.name, row.commercial, row.operational, row.total])];
    const url = URL.createObjectURL(new Blob(['\ufeff' + rows.map((row) => row.map(safe).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
    const link = el('a', { href: url, download: 'Inversion_por_proyecto_' + (document.getElementById('mes')?.value || 'acumulado') + '.csv' });
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  function renderTable() {
    const matches = options();
    const pages = Math.max(1, Math.ceil(matches.length / size));
    page = Math.max(1, Math.min(page, pages));
    const table = el('table', { class: 'inv-person-project-table' });
    const heads = [['name', 'Proyecto'], ['commercial', 'Comercial'], ['operational', 'Operativa'], ['total', 'Total']];
    table.append(el('thead', {}, el('tr', {}, ...heads.map(([key, label]) => el('th', { scope: 'col', 'aria-sort': sort === key ? descending ? 'descending' : 'ascending' : 'none' },
      button(label + (sort === key ? descending ? ' ↓' : ' ↑' : ''), () => { descending = sort === key ? !descending : key !== 'name'; sort = key; page = 1; renderTable(); }))))));
    const body = el('tbody');
    for (const row of matches.slice((page - 1) * size, page * size)) {
      body.append(el('tr', {}, el('td', {}, folder(), el('span', { text: row.name })),
        el('td', { text: hours(row.commercial) }), el('td', { text: hours(row.operational) }), el('td', {}, el('b', { text: hours(row.total) }))));
    }
    if (!matches.length) body.append(el('tr', {}, el('td', { colspan: 4, text: 'No hay proyectos con esa búsqueda.' })));
    table.append(body);
    panel.querySelector('.inv-project-results').replaceChildren(table);
    const previous = button('‹', () => { page--; renderTable(); }, { 'aria-label': 'Página anterior' });
    const next = button('›', () => { page++; renderTable(); }, { 'aria-label': 'Página siguiente' });
    previous.disabled = page === 1;
    next.disabled = page === pages;
    const select = el('select', { 'aria-label': 'Proyectos por página', onchange: (event) => { size = Number(event.target.value); page = 1; renderTable(); } },
      ...[5, 10, 25].map((number) => el('option', { value: number, text: number, selected: number === size })));
    panel.querySelector('.inv-detail-pagination').replaceChildren(previous, el('span', { text: `${page} / ${pages}` }), next,
      el('label', {}, 'Mostrar ', select, ' por página'));
    panel.querySelector('.inv-detail-count').textContent = `Horas por proyecto (${matches.length})`;
  }
  function open(index, trigger) {
    active = index; query = ''; sort = 'total'; descending = true; page = 1;
    opener = trigger;
    const person = people[index];
    const commercial = person.total ? person.commercial / person.total * 100 : 0;
    const operational = person.total ? person.operational / person.total * 100 : 0;
    panel.hidden = false;
    card.classList.add('is-open');
    document.querySelectorAll('[data-investment-person]').forEach((node) => node.setAttribute('aria-pressed', String(Number(node.getAttribute('data-investment-person')) === index)));
    document.querySelectorAll('[data-investment-person-row]').forEach((node) => node.classList.toggle('selected', Number(node.getAttribute('data-investment-person-row')) === index));
    const heading = el('h3', { id: 'inv-person-heading', tabindex: '-1', text: person.name });
    panel.replaceChildren(
      el('header', { class: 'inv-person-head' }, el('div', {}, heading, el('span', { text: person.area })), button('×', close, { 'aria-label': 'Cerrar detalle del recurso' })),
      el('div', { class: 'inv-person-totals' }, ...[['Comercial', person.commercial, 'commercial'], ['Operativa', person.operational, 'operational'], ['Total', person.total, 'total']].map(([label, value, tone]) => el('div', { class: tone }, el('span', { text: label }), el('strong', { text: hours(value) })))),
      el('div', { class: 'inv-person-project-heading' }, el('h4', { class: 'inv-detail-count', text: 'Horas por proyecto' }), button('↓', download, { 'aria-label': 'Descargar proyectos del recurso' })),
      el('input', { type: 'search', class: 'inv-project-search', placeholder: 'Buscar proyecto…', 'aria-label': 'Buscar proyecto del recurso', oninput: (event) => { query = event.target.value; page = 1; renderTable(); } }),
      el('div', { class: 'inv-project-results' }), el('div', { class: 'inv-detail-pagination' }),
      el('div', { class: 'inv-person-distribution' },
        svg('svg', { viewBox: '0 0 500 20', role: 'img', 'aria-label': `Comercial ${formatNumber(commercial, 1)}%, operativa ${formatNumber(operational, 1)}%` },
          svg('rect', { width: 500, height: 20, rx: 10, fill: '#eee8fc' }),
          svg('rect', { width: commercial * 5, height: 20, fill: '#8130ff' }),
          svg('rect', { x: commercial * 5, width: operational * 5, height: 20, fill: '#00bf88' })),
        el('div', { class: 'inv-person-percentages' }, el('span', {}, el('i', { class: 'inv-dot commercial' }), `Comercial: ${formatNumber(commercial, 1)}% (${hours(person.commercial)})`),
          el('span', {}, el('i', { class: 'inv-dot operational' }), `Operativa: ${formatNumber(operational, 1)}% (${hours(person.operational)})`)))
    );
    renderTable();
    heading.focus({ preventScroll: true });
    if (window.innerWidth < 850) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  document.querySelectorAll('[data-investment-person]').forEach((node) => node.addEventListener('click', () => open(Number(node.getAttribute('data-investment-person')), node)));
  panel.addEventListener('keydown', (event) => { if (event.key === 'Escape') close(); });
}
