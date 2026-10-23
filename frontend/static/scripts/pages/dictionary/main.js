// @ts-check
// Diccionario de datos: las definiciones llegan de la API y se filtran aqui,
// con la busqueda guardada en la URL.
import { apiGet } from '#app/data/api-client.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatDate, plain } from '#app/lib/format.js';
import { showError, showLoading } from '#app/ui/states.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const content = byId('dictionary-content');
const search = /** @type {HTMLInputElement} */ (byId('dictionary-search'));
const clear = byId('dictionary-clear');
const count = byId('dictionary-count');

/** @param {any[]} concepts */
function render(concepts) {
  const rows = concepts.map((concept) => {
    const row = el(
      'tr',
      { 'data-dictionary-entry': '' },
      el('th', { scope: 'row', text: concept.name }),
      el('td', { 'data-label': 'Definición y cálculo', text: concept.definition }),
      el('td', { 'data-label': 'Fuente / validación', class: 'dictionary-source', text: concept.source }),
    );
    return { row, text: plain(row.textContent || '').trim() };
  });
  const empty = el(
    'tr',
    { id: 'dictionary-empty', hidden: true },
    el('td', { colspan: 3 }, el('strong', { text: 'No encontramos coincidencias.' }), el('span', { text: 'Prueba con otro concepto o limpia la búsqueda para ver todas las definiciones.' })),
  );
  content.removeAttribute('aria-busy');
  content.replaceChildren(
    el(
      'table',
      { class: 'dictionary-table' },
      el('caption', { class: 'portal-sr-only', text: 'Conceptos, definición y cálculo, y fuente de los indicadores del dashboard.' }),
      el('thead', {}, el('tr', {}, ...['Concepto', 'Definición y cálculo', 'Fuente / validación'].map((text) => el('th', { scope: 'col', text })))),
      el('tbody', {}, ...rows.map((r) => r.row), empty),
    ),
  );

  /** @param {boolean} [updateUrl] */
  function apply(updateUrl = true) {
    const query = plain(search.value).trim();
    let matches = 0;
    for (const { row, text } of rows) {
      row.hidden = Boolean(query) && !text.includes(query);
      if (!row.hidden) matches += 1;
    }
    count.textContent = query ? `${matches} de ${rows.length} conceptos` : `${rows.length} conceptos`;
    empty.hidden = matches > 0;
    clear.hidden = !search.value;
    if (updateUrl) writeParams({ q: search.value.trim() });
  }
  search.value = readParams().get('q') || '';
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
  apply(false);
}

async function load() {
  showLoading(content, 'Cargando definiciones…');
  try {
    const { data, meta } = await apiGet('reference/glossary/');
    byId('dictionary-updated').textContent = `Definiciones al ${formatDate(meta.definitions_date)}`;
    render(data.concepts);
  } catch (error) {
    showError(content, error, { onRetry: load });
  }
}

load();
