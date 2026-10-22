// @ts-check
// Diccionario de datos: lista los conceptos de la API y filtra sin recargar,
// guardando la busqueda en la URL.
import { apiGet } from '#app/data/api-client.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatDate, plain } from '#app/lib/format.js';
import { showError, showLoading } from '#app/ui/states.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const holder = byId('dic-table');
const search = /** @type {HTMLInputElement} */ (byId('dic-search'));
const clear = /** @type {HTMLButtonElement} */ (byId('dic-clear'));
const count = byId('dic-count');

/** @type {{row: HTMLElement, text: string}[]} */
let entries = [];
let empty = el('tr');

function apply(updateUrl = true) {
  const query = plain(search.value.trim());
  let shown = 0;
  for (const { row, text } of entries) {
    row.hidden = Boolean(query) && !text.includes(query);
    if (!row.hidden) shown += 1;
  }
  empty.hidden = shown > 0;
  count.textContent = query ? `${shown} de ${entries.length} conceptos` : `${entries.length} conceptos`;
  clear.hidden = !search.value;
  if (updateUrl) writeParams({ q: search.value.trim() });
}

/** @param {any} data */
function render(data) {
  empty = el('tr', { hidden: true }, el('td', { colspan: 3 }, el('strong', { text: 'No encontramos coincidencias.' }), ' Prueba con otro concepto o limpia la búsqueda para ver todas las definiciones.'));
  entries = data.concepts.map((/** @type {any} */ c) => ({
    row: el('tr', {}, el('th', { scope: 'row', text: c.name }), el('td', { text: c.definition }), el('td', { class: 'source', text: c.source })),
    text: plain(`${c.name} ${c.definition} ${c.source}`),
  }));
  holder.replaceChildren(
    el(
      'div',
      { class: 'dic-scroll' },
      el(
        'table',
        {},
        el('caption', { class: 'sr-only', text: 'Conceptos, definición y cálculo, y fuente de los indicadores del dashboard.' }),
        el('thead', {}, el('tr', {}, ...['Concepto', 'Definición y cálculo', 'Fuente / validación'].map((h) => el('th', { scope: 'col', text: h })))),
        el('tbody', {}, ...entries.map((e) => e.row), empty),
      ),
    ),
  );
  search.value = readParams().get('q') || '';
  apply(false);
}

async function load() {
  showLoading(holder, 'Cargando el diccionario…');
  try {
    const body = await apiGet('reference/glossary/');
    byId('dic-updated').textContent = `Definiciones al ${formatDate(body.meta.definitions_date)}`;
    render(body.data);
  } catch (error) {
    showError(holder, error, { onRetry: load });
  }
}

search.addEventListener('input', () => apply());
clear.addEventListener('click', () => {
  search.value = '';
  apply();
  search.focus();
});
addEventListener('popstate', () => {
  search.value = readParams().get('q') || '';
  apply(false);
});
load();
