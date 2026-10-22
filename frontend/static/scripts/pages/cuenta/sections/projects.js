// @ts-check
// Tabla de proyectos de la cuenta: busqueda, estado y paginas de seis.
import { withReturn } from '#app/data/navigation.js';
import { el } from '#app/lib/dom.js';
import { formatNumber, plain } from '#app/lib/format.js';
import { pageOf, stageTone } from '#app/lib/account-metrics.js';

const PAGE_SIZE = 6;
const HEADERS = ['Proyecto', 'Modelo', 'Etapa', 'Estado', 'Delivery Manager', 'Presupuesto', 'Consumo', 'NPS'];

/** @param {number | null | undefined} value */
const hours = (value) => (value == null ? 'Sin datos' : `${formatNumber(value, 1)} h`);

/** @param {string | null | undefined} text */
const badge = (text) => el('span', { class: `badge ${stageTone(text)}`, text: text || '' });

/**
 * @param {import('#app/lib/account-metrics.js').AccountProject} project
 * @param {string} projectUrl Plantilla con el marcador PROJECT_ID.
 */
function row(project, projectUrl) {
  const link = withReturn(projectUrl.replace('PROJECT_ID', encodeURIComponent(project.id)));
  const burn = project.clockify_pending ? 'Consultando…' : project.clockify_error ? 'No disponible' : hours(project.burn);
  return el(
    'tr',
    { dataset: { project: project.id } },
    el('td', {}, el('a', { href: link, text: project.name || project.id }), el('small', {}, el('a', { href: link, text: project.id }))),
    el('td', {}, el('span', { class: 'badge purple', text: project.service || '' })),
    el('td', {}, badge(project.stage)),
    el('td', {}, badge(project.state)),
    el('td', { text: project.manager || '' }),
    el('td', { text: hours(project.budget ?? 0) }),
    el('td', { class: 'cuenta-burn', text: burn }),
    el('td', { text: project.nps == null ? '—' : String(project.nps) }),
  );
}

/**
 * Pinta la tabla y devuelve como repintarla con otros datos sin perder
 * la busqueda ni la pagina.
 * @param {HTMLElement} container
 * @param {string} projectUrl
 */
export function createProjectsTable(container, projectUrl) {
  let template = projectUrl;
  const search = /** @type {HTMLInputElement} */ (
    el('input', { id: 'cuenta-search', type: 'search', placeholder: 'Buscar proyecto, DM o servicio…', 'aria-label': 'Buscar proyecto' })
  );
  const state = /** @type {HTMLSelectElement} */ (el('select', { id: 'cuenta-state', 'aria-label': 'Filtrar proyectos por estado' }));
  const body = el('tbody');
  const label = el('span', { id: 'cuenta-page-label', role: 'status', 'aria-live': 'polite' });
  const prev = /** @type {HTMLButtonElement} */ (el('button', { type: 'button', class: 'btn btn-ghost', 'aria-label': 'Página anterior', text: '←' }));
  const next = /** @type {HTMLButtonElement} */ (el('button', { type: 'button', class: 'btn btn-ghost', 'aria-label': 'Página siguiente', text: '→' }));
  container.append(
    el(
      'section',
      { class: 'card cuenta-projects' },
      el('h2', { id: 'cuenta-project-table', text: 'Proyectos de la cuenta' }),
      el('div', { class: 'cuenta-toolbar' }, search, state),
      el('div', { class: 'cuenta-scroll' }, el('table', {}, el('thead', {}, el('tr', {}, ...HEADERS.map((h) => el('th', { scope: 'col', text: h })))), body)),
      el('div', { class: 'cuenta-pages' }, label, el('div', {}, prev, ' ', next)),
    ),
  );

  /** @type {import('#app/lib/account-metrics.js').AccountProject[]} */
  let projects = [];
  let page = 1;

  function draw() {
    const needle = plain(search.value);
    const matches = projects.filter(
      (p) => plain([p.id, p.name, p.service, p.stage, p.state, p.manager].join(' ')).includes(needle) && (!state.value || (p.state || 'Sin estado') === state.value),
    );
    const view = pageOf(matches, page, PAGE_SIZE);
    page = view.page;
    body.replaceChildren(...(view.items.length ? view.items.map((p) => row(p, template)) : [el('tr', {}, el('td', { colspan: HEADERS.length, text: 'Sin proyectos registrados.' }))]));
    label.textContent = `Mostrando ${view.from}–${view.to} de ${matches.length} proyectos`;
    prev.disabled = view.page === 1;
    next.disabled = view.page === view.pages;
  }

  search.addEventListener('input', () => ((page = 1), draw()));
  state.addEventListener('change', () => ((page = 1), draw()));
  prev.addEventListener('click', () => (page--, draw()));
  next.addEventListener('click', () => (page++, draw()));

  return {
    /** @param {string} url Plantilla del enlace al proyecto, con PROJECT_ID. */
    setProjectUrl(url) {
      template = url;
    },
    /** @param {import('#app/lib/account-metrics.js').AccountProject[]} next */
    update(next) {
      projects = next;
      const chosen = state.value;
      const names = [...new Set(next.map((p) => p.state || 'Sin estado'))];
      state.replaceChildren(el('option', { value: '', text: 'Todos los estados' }), ...names.map((n) => el('option', { value: n, text: n })));
      state.value = names.includes(chosen) ? chosen : '';
      draw();
    },
  };
}
