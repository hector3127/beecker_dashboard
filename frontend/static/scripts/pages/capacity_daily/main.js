// @ts-check
// Una lectura de la API por mes; la jornada y los filtros se recalculan aqui.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { csv, options, selectedRows } from './model.js';
import { icon, render } from './view.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
/** @type {any} */
const state = { mes: '', data: null, request: 0, q: '', rol: '', banda: '', jornada: 8, view: 'matrix', page: 1, size: 30, detailResource: '' };
/** @type {AbortController | null} */
let current = null;
const monthInput = /** @type {HTMLInputElement} */ (byId('ci-month'));
const paint = () => render(byId('ci-content'), state, paint);

/** @param {string} text @param {boolean} [error] */
function message(text, error = false) {
  byId('ci-status').textContent = text;
  byId('ci-status').classList.toggle('ci-error', error);
}

function fillFilters() {
  monthInput.value = state.data.mes;
  byId('ci-monthchip').textContent = '▣ Mes ' + state.data.mes;
  for (const [field, id, title] of [['rol', 'ci-role', 'Todos los roles'], ['banda', 'ci-band', 'Todas las bandas']]) {
    const select = /** @type {HTMLSelectElement} */ (byId(id));
    select.replaceChildren(el('option', { value: '', text: title }),
      ...options(state.data, /** @type {'rol'|'banda'} */ (field)).map((v) => el('option', { value: v, text: v })));
    select.value = state[field];
  }
}

async function load() {
  current?.abort();
  current = new AbortController();
  const signal = current.signal, token = ++state.request;
  message('Leyendo Bandas/rol y Clockify…');
  try {
    const { data } = await apiGet('screens/capacidad/diaria/', { mes: state.mes }, { signal, timeout: 90000 });
    if (token !== state.request) return;
    if (!data || !data.ok) { message(data?.error || 'No se pudieron leer las hojas.', true); return; }
    state.data = data;
    state.mes = data.mes;
    state.detailResource = '';
    fillFilters();
    paint();
    message(`Mes ${data.mes} · Bandas/rol + Clockify · ${data.resumen.personas} personas vigentes`);
  } catch (error) {
    if (!signal.aborted && token === state.request) message(error instanceof Error ? error.message : String(error), true);
  }
}

document.querySelectorAll('[data-icon]').forEach((placeholder) => {
  const name = /** @type {Parameters<typeof icon>[0]} */ (placeholder.getAttribute('data-icon'));
  const node = icon(name);
  if (placeholder.classList.contains('ci-icon')) placeholder.append(node);
  else placeholder.replaceWith(node);
});
monthInput.addEventListener('change', () => {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(monthInput.value) || state.mes === monthInput.value) return;
  state.mes = monthInput.value;
  state.page = 1;
  void load();
});
byId('ci-jornada').addEventListener('change', (event) => {
  const value = Number(/** @type {HTMLInputElement} */ (event.target).value);
  if (value >= 1 && value <= 24) { state.jornada = value; paint(); }
});
for (const [id, property, event] of [['ci-search', 'q', 'input'], ['ci-role', 'rol', 'change'], ['ci-band', 'banda', 'change']]) {
  byId(id).addEventListener(event, (event) => {
    state[property] = /** @type {HTMLInputElement} */ (event.target).value;
    state.page = 1;
    paint();
  });
}
byId('ci-refresh').addEventListener('click', () => { void load(); });
byId('ci-export').addEventListener('click', () => {
  if (!state.data) return;
  const url = URL.createObjectURL(new Blob([csv(state.data, selectedRows(state.data, state))], { type: 'text/csv;charset=utf-8' }));
  el('a', { href: url, download: 'Capacidad_instalada_' + state.mes + '.csv' }).click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
window.addEventListener('pagehide', () => { state.request += 1; current?.abort(); });
const requested = new URLSearchParams(location.search).get('mes');
const now = new Date();
state.mes = /^\d{4}-(0[1-9]|1[0-2])$/.test(requested || '') ? requested : now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
monthInput.value = state.mes;
void load();
