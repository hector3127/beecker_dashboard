// @ts-check
// Diccionario: búsqueda, categorías y orden sin consultar nuevamente las fuentes.
import { apiGet } from '#app/data/api-client.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatDate, plain } from '#app/lib/format.js';
import { showError, showLoading } from '#app/ui/states.js';
import { CATEGORIES, presentation, dictionaryIcon } from './presentation.js';

const byId = id => document.getElementById(id);
const content = byId('dictionary-content');
const search = /** @type {HTMLInputElement} */ (byId('dictionary-search'));
const category = /** @type {HTMLSelectElement} */ (byId('dictionary-category'));
const clear = byId('dictionary-clear');
const count = byId('dictionary-count');

/** @param {any[]} concepts */
function render(concepts) {
  const rows = concepts.map((concept, index) => {
    const view = presentation(concept);
    const row = el('tr', { 'data-dictionary-entry': '', 'data-category': view.category },
      el('th', { scope:'row' }, el('div', { class:'dictionary-concept' },
        el('span', { class:`dictionary-entry-icon ${view.tone}` }, dictionaryIcon(view.icon)),
        el('span', {text:concept.name}))),
      el('td', { 'data-label':'Qué mide' }, el('p', {text:view.definition})),
      el('td', { 'data-label':'Cálculo' }, el('p', {class:'dictionary-formula',text:view.formula})));
    return {row,index,category:view.category,text:plain(`${concept.name} ${view.definition} ${view.formula}`),
      name:concept.name,definition:view.definition,calculation:view.formula};
  });
  let sortKey = '';
  let direction = 'asc';
  const keys = ['name','definition','calculation'];
  const labels = ['Indicador','Qué mide','Cálculo'];
  const headers = keys.map((key, index) => el('th', { scope:'col','aria-sort':'none' },
    el('button', {type:'button','data-dictionary-sort':key}, labels[index],
      el('span', {'aria-hidden':'true',class:'dictionary-sort-mark',text:'↕'}))));
  const empty = el('tr', {id:'dictionary-empty',hidden:true},
    el('td', {colspan:3}, el('strong', {text:'No encontramos coincidencias.'}),
      el('span', {text:'Prueba con otro concepto o limpia los filtros para ver todas las definiciones.'})));
  const body = el('tbody', {}, ...rows.map(r => r.row), empty);
  content.removeAttribute('aria-busy');
  content.replaceChildren(el('table', {class:'dictionary-table'},
    el('caption', {class:'portal-sr-only',text:'Indicadores, definición y cálculo del dashboard.'}),
    el('thead', {}, el('tr', {}, ...headers)), body));
  category.replaceChildren(el('option', {value:'',text:'Todas las categorías'}),
    ...CATEGORIES.map(text => el('option', {value:text,text})));
  const tabs = ['',...CATEGORIES].map(value => el('button', {
    type:'button','data-dictionary-category':value,'aria-pressed':'false',text:value || 'Todos',
    onclick:() => {category.value = value;apply();},
  }));
  byId('dictionary-categories').replaceChildren(...tabs);

  function apply(updateUrl = true) {
    const query = plain(search.value).trim();
    let matches = 0;
    for (const item of rows) {
      item.row.hidden = Boolean(query && !item.text.includes(query)) || Boolean(category.value && item.category !== category.value);
      if (!item.row.hidden) matches += 1;
    }
    count.textContent = query || category.value ? `${matches} de ${rows.length} conceptos` : `${rows.length} conceptos`;
    empty.hidden = matches > 0;
    tabs.forEach(tab => tab.setAttribute('aria-pressed', String(tab.dataset.dictionaryCategory === category.value)));
    const sorted = [...rows].sort((a,b) => sortKey
      ? a[sortKey].localeCompare(b[sortKey], 'es', {sensitivity:'base'}) * (direction === 'desc' ? -1 : 1)
      : a.index - b.index);
    body.append(...sorted.map(r => r.row), empty);
    headers.forEach((header,index) => {
      header.setAttribute('aria-sort', sortKey === keys[index] ? direction === 'asc' ? 'ascending' : 'descending' : 'none');
      header.querySelector('.dictionary-sort-mark').textContent = sortKey === keys[index] ? direction === 'asc' ? '↑' : '↓' : '↕';
    });
    if (updateUrl) writeParams({q:search.value.trim(),categoria:category.value,orden:sortKey,sentido:sortKey ? direction : ''});
  }
  function restore() {
    const params = readParams();
    search.value = params.get('q') || '';
    const selected = params.get('categoria') || '';
    category.value = CATEGORIES.includes(selected) ? selected : '';
    sortKey = keys.includes(params.get('orden')) ? params.get('orden') : '';
    direction = params.get('sentido') === 'desc' ? 'desc' : 'asc';
    apply(false);
  }
  search.addEventListener('input', () => apply());
  category.addEventListener('change', () => apply());
  headers.forEach((header,index) => header.querySelector('button').addEventListener('click', () => {
    direction = sortKey === keys[index] && direction === 'asc' ? 'desc' : 'asc';
    sortKey = keys[index];apply();
  }));
  clear.addEventListener('click', () => {
    search.value = '';category.value = '';sortKey = '';direction = 'asc';apply();search.focus();
  });
  addEventListener('popstate', restore);
  restore();
}

async function load() {
  showLoading(content, 'Cargando definiciones…');
  try {
    const {data,meta} = await apiGet('reference/glossary/');
    byId('dictionary-updated').textContent = `Definiciones al ${formatDate(meta.definitions_date)}`;
    render(data.concepts);
  } catch (error) {
    showError(content, error, {onRetry:load});
  }
}
load();
