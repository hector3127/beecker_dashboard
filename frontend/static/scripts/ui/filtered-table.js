// @ts-check
// Tabla con busqueda, filtro por una columna, orden por encabezado y paginas.
import { el } from '#app/lib/dom.js';
import { plain } from '#app/lib/format.js';
import { pageOf } from '#app/lib/account-metrics.js';

const PAGE_SIZE = 8;

/**
 * @param {HTMLElement} root
 * @param {object} options
 * @param {string[]} options.headers
 * @param {string[][]} options.rows Texto ya formateado de cada celda.
 * @param {number} options.filterColumn Columna que alimenta el filtro de estado.
 * @param {string} options.placeholder
 */
export function filteredTable(root, { headers, rows, filterColumn, placeholder }) {
  const search = /** @type {HTMLInputElement} */ (el('input', { type: 'search', placeholder, 'aria-label': placeholder }));
  const stage = /** @type {HTMLSelectElement} */ (el('select', { 'aria-label': 'Filtrar por estado' }, el('option', { value: '', text: 'Todos los estados' })));
  for (const value of [...new Set(rows.map((row) => row[filterColumn]))].filter(Boolean)) stage.append(el('option', { value, text: value }));
  const body = el('tbody');
  const info = el('span', { role: 'status', 'aria-live': 'polite' });
  const prev = /** @type {HTMLButtonElement} */ (el('button', { type: 'button', class: 'btn btn-ghost', 'aria-label': 'Página anterior', text: '←' }));
  const next = /** @type {HTMLButtonElement} */ (el('button', { type: 'button', class: 'btn btn-ghost', 'aria-label': 'Página siguiente', text: '→' }));
  let page = 1;
  let sort = 0;
  let ascending = true;

  const heads = headers.map((label, index) =>
    el('th', { scope: 'col' }, el('button', { type: 'button', class: 'sort', text: `${label} ↕`, onclick: () => ((ascending = sort === index ? !ascending : true), (sort = index), draw()) })),
  );

  function draw() {
    const needle = plain(search.value);
    const found = rows
      .filter((row) => plain(row.join(' ')).includes(needle) && (!stage.value || row[filterColumn] === stage.value))
      .sort((a, b) => a[sort].localeCompare(b[sort], 'es', { numeric: true }) * (ascending ? 1 : -1));
    const view = pageOf(found, page, PAGE_SIZE);
    page = view.page;
    body.replaceChildren(...view.items.map((row) => el('tr', {}, ...row.map((text) => el('td', { text })))));
    info.textContent = `${found.length} registros · página ${view.page} de ${view.pages}`;
    prev.disabled = view.page === 1;
    next.disabled = view.page === view.pages;
  }

  search.addEventListener('input', () => ((page = 1), draw()));
  stage.addEventListener('change', () => ((page = 1), draw()));
  prev.addEventListener('click', () => (page--, draw()));
  next.addEventListener('click', () => (page++, draw()));
  root.append(
    el('div', { class: 'detail-controls' }, search, stage),
    el('div', { class: 'detail-scroll' }, el('table', {}, el('thead', {}, el('tr', {}, ...heads)), body)),
    el('div', { class: 'detail-pager' }, info, el('div', {}, prev, ' ', next)),
  );
  draw();
}
