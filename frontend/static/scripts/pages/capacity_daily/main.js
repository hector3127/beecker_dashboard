// @ts-check
// Dos lecturas API y un maximo de dos consultas de proyectos simultaneas.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { computed, csv, key, selected } from './model.js';
import { icon, render } from './view.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
/** @type {any} */
const state = { mes: '', base: null, meta: new Map(), request: 0, q: '', tecnologia: '', concepto: '', jornada: 8, view: 'matrix', page: 1, size: 30 };
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
  const data = state.base;
  byId('ci-monthchip').textContent = '▣ Mes ' + data.mes;
  byId('ci-bandchip').textContent = '◇ Banda: ' + (data.bandaColumna || 'NA');
  monthInput.value = data.mes;
  for (const [property, id, title] of [['tecnologia', 'ci-role', 'Todas las tecnologías'], ['concepto', 'ci-concept', 'Todos los conceptos']]) {
    const select = /** @type {HTMLSelectElement} */ (byId(id));
    const values = [...new Set(data.filas.map((/** @type {any} */ row) => row[property]).filter(Boolean))].sort();
    select.replaceChildren(el('option', { value: '', text: title }), ...values.map((v) => el('option', { value: v, text: v })));
    select.value = state[property];
  }
}

/** @param {boolean} force */
async function load(force) {
  current?.abort();
  current = new AbortController();
  const signal = current.signal, token = ++state.request, queryMonth = state.mes;
  message('Leyendo Recursos y Bandas/rol…');
  try {
    const { data } = await apiGet('screens/capacidad/diaria/', { mes: queryMonth }, { signal, timeout: 90000 });
    if (token !== state.request) return;
    if (!data || !data.ok) { message(data?.error || 'No se pudieron leer las hojas.', true); return; }
    state.base = data;
    state.mes = data.mes;
    const resolvedMonth = data.mes;
    fillFilters();
    paint();
    const queue = [...new Map(data.filas.filter((/** @type {any} */ f) => f.idProyecto).map((/** @type {any} */ f) => [key(f), f])).values()]
      .filter((f) => force || !state.meta.has(key(f)) || state.meta.get(key(f)).mes !== state.mes || !state.meta.get(key(f)).ok);
    let next = 0, completed = 0;
    const progress = () => message(queue.length ? `MPB/Azure + Clockify: ${completed} / ${queue.length} proyectos consultados` : `Datos disponibles · ${data.filas.length} asignaciones`);
    progress();
    async function worker() {
      while (token === state.request && next < queue.length) {
        const assignment = queue[next++];
        let result;
        try {
          result = (await apiGet('screens/capacidad/diaria/proyecto/', {
            proyecto: assignment.idProyecto, iteration: assignment.iteration || '', mes: resolvedMonth, ...(force ? { actualizar: '1' } : {}),
          }, { signal, timeout: 90000 })).data;
        } catch (error) {
          if (signal.aborted || token !== state.request) return;
          result = { ok: false, error: error instanceof Error ? error.message : String(error) };
        }
        if (token !== state.request) return;
        state.meta.set(key(assignment), Object.assign({ mes: resolvedMonth }, result || { ok: false, error: 'Clockify no devolvió datos' }));
        completed += 1;
        paint();
        progress();
      }
    }
    await Promise.all([worker(), worker()]);
    if (token !== state.request) return;
    paint();
    message(`Mes ${state.mes} · ${data.fuentes.join(' + ')} + Clockify · Banda: ${data.bandaColumna || 'NA'}`);
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
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(monthInput.value)) return;
  if (state.mes !== monthInput.value) state.meta.clear();
  state.mes = monthInput.value;
  state.page = 1;
  void load(false);
});
byId('ci-jornada').addEventListener('change', (event) => {
  const value = Number(/** @type {HTMLInputElement} */ (event.target).value);
  if (value >= 1 && value <= 24) { state.jornada = value; paint(); }
});
for (const [id, property, event] of [['ci-search', 'q', 'input'], ['ci-role', 'tecnologia', 'change'], ['ci-concept', 'concepto', 'change']]) {
  byId(id).addEventListener(event, (event) => {
    state[property] = /** @type {HTMLInputElement} */ (event.target).value;
    state.page = 1;
    paint();
  });
}
byId('ci-refresh').addEventListener('click', () => { void load(true); });
byId('ci-export').addEventListener('click', () => {
  if (!state.base) return;
  const data = computed(state);
  const url = URL.createObjectURL(new Blob([csv(data, selected(data.all, state))], { type: 'text/csv;charset=utf-8' }));
  const link = el('a', { href: url, download: 'Capacidad_instalada_' + state.mes + '.csv' });
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
window.addEventListener('pagehide', () => { state.request += 1; current?.abort(); });
const requested = new URLSearchParams(location.search).get('mes');
const now = new Date();
state.mes = /^\d{4}-(0[1-9]|1[0-2])$/.test(requested || '') ? requested : now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
monthInput.value = state.mes;
void load(false);
