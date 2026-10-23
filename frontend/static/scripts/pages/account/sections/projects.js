// @ts-check
// Proyectos de la cuenta, con busqueda por texto, filtro por estado y paginas.
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';

const PAGE = 6;
const HEADERS = ['Proyecto', 'Modelo', 'Etapa', 'Estado', 'Delivery Manager', 'Presupuesto', 'Consumo', 'NPS'];

/** Color de la etiqueta segun su texto: verde, rojo, amarillo o morado. @param {string} text */
function tone(text) {
  const lower = text.trim().toLowerCase();
  if (/completed|completado|finalizado|producción/.test(lower)) return 'is-green';
  if (/cancel/.test(lower)) return 'is-red';
  if (/suspend/.test(lower)) return 'is-yellow';
  return 'is-purple';
}

/** @param {string} text */
const badge = (text) => el('span', { class: `account-badge account-conditional ${tone(text)}`, text });

/** @param {any} project */
const burnText = (project) => {
  if (project.clockify_pending) return 'Consultando…';
  return project.burn !== null && project.burn !== undefined ? `${formatNumber(project.burn, 1)} h` : 'Sin datos';
};

/**
 * @param {any[]} projects
 * @param {string} projectUrl Con el marcador project-placeholder.
 * @returns {{section: HTMLElement, setBurn: (id: string, text: string) => void}}
 */
export function renderProjects(projects, projectUrl) {
  const link = (/** @type {string} */ id, /** @type {string} */ text) =>
    el('a', { href: projectUrl.replace('project-placeholder', encodeURIComponent(id)), text });
  const states = [...new Set(projects.map((p) => p.state).filter(Boolean))];
  const rows = projects.map((p) => {
    const burn = el('td', { class: 'account-project-burn', text: burnText(p) });
    const tr = el(
      'tr',
      { 'data-project': p.id, 'data-state': p.state ?? '', 'data-burn': p.burn ?? 0 },
      el('td', {}, link(p.id, p.name), el('small', {}, link(p.id, p.id))),
      el('td', {}, el('span', { class: 'account-badge', text: p.service ?? '' })),
      el('td', {}, badge(p.stage ?? '')),
      el('td', {}, badge(p.state ?? '')),
      el('td', { text: p.manager ?? '' }),
      el('td', { text: `${formatNumber(p.budget ?? 0, 1)} h` }),
      burn,
      el('td', { text: p.nps !== null && p.nps !== undefined ? String(p.nps) : '—' }),
    );
    return { tr, burn };
  });
  const search = /** @type {HTMLInputElement} */ (el('input', { id: 'account-search', placeholder: 'Buscar proyecto, DM o servicio…', 'aria-label': 'Buscar proyecto' }));
  const state = /** @type {HTMLSelectElement} */ (
    el('select', { id: 'account-state' }, el('option', { value: '', text: 'Todos los estados' }), ...states.map((name) => el('option', { text: name })))
  );
  const label = el('span', { id: 'account-page-label' });
  const prev = /** @type {HTMLButtonElement} */ (el('button', { type: 'button', id: 'account-prev', text: '←' }));
  const next = /** @type {HTMLButtonElement} */ (el('button', { type: 'button', id: 'account-next', text: '→' }));
  const empty = el('tr', {}, el('td', { colspan: 8, text: 'Sin proyectos registrados.' }));
  const body = el('tbody', {}, ...(rows.length ? rows.map((r) => r.tr) : [empty]));
  let page = 1;

  function filter(reset = true) {
    if (reset) page = 1;
    const query = search.value.toLocaleLowerCase('es');
    const matches = rows.filter(({ tr }) => (tr.textContent || '').toLocaleLowerCase('es').includes(query) && (!state.value || tr.dataset.state === state.value));
    const pages = Math.max(1, Math.ceil(matches.length / PAGE));
    page = Math.max(1, Math.min(page, pages));
    for (const { tr } of rows) tr.hidden = true;
    for (const { tr } of matches.slice((page - 1) * PAGE, page * PAGE)) tr.hidden = false;
    label.textContent = `Mostrando ${matches.length ? (page - 1) * PAGE + 1 : 0}–${Math.min(page * PAGE, matches.length)} de ${matches.length} proyectos`;
    prev.disabled = page === 1;
    next.disabled = page === pages;
  }
  prev.addEventListener('click', () => {
    page -= 1;
    filter(false);
  });
  next.addEventListener('click', () => {
    page += 1;
    filter(false);
  });
  search.addEventListener('input', () => filter());
  state.addEventListener('change', () => filter());

  const section = el(
    'section',
    { class: 'account-card' },
    el('h2', { id: 'account-project-table', text: 'Proyectos de la cuenta' }),
    el('div', { class: 'account-toolbar' }, search, state),
    el('div', { class: 'account-scroll' }, el('table', {}, el('thead', {}, el('tr', {}, ...HEADERS.map((text) => el('th', { text })))), body)),
    el('div', { class: 'account-table-pages' }, label, el('div', {}, prev, ' ', next)),
  );
  filter();
  return {
    section,
    setBurn(id, text) {
      const row = rows.find(({ tr }) => String(tr.dataset.project).toLowerCase() === String(id).toLowerCase());
      if (row) row.burn.textContent = text;
    },
  };
}
