// @ts-check
// Operativa: pinta el ultimo corte y despues refresca por bloques, como la
// pantalla anterior: primero proyectos y estados; luego, en paralelo, EVA-04,
// inversion, capacidad y consumo (salud). La facturabilidad va aparte.
import { apiGet } from '#app/data/api-client.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatDateTime } from '#app/lib/format.js';
import { slugify } from '#app/lib/slug.js';
import { renderBilling } from './sections/billing.js';
import { renderCapacity } from './sections/capacity.js';
import { renderEva } from './sections/eva.js';
import { renderHealth } from './sections/health.js';
import { renderManagers } from './sections/managers.js';
import { renderMetrics } from './sections/metrics.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const root = byId('ops-dashboard');
const urls = {
  account: /** @type {string} */ (root.dataset.accountUrl),
  managerUrl: /** @type {string} */ (root.dataset.managerUrl),
  investmentUrl: /** @type {string} */ (root.dataset.investmentUrl),
  eva1: /** @type {string} */ (root.dataset.eva1Url),
  eva3: /** @type {string} */ (root.dataset.eva3Url),
  eva4: /** @type {string} */ (root.dataset.eva4Url),
};
const regions = {
  alerts: byId('ops-alerts'),
  cut: byId('ops-cut'),
  status: byId('ops-refresh-status'),
  refresh: /** @type {HTMLButtonElement} */ (byId('ops-refresh-button')),
  metrics: byId('ops-metrics'),
  health: byId('ops-health'),
  managers: byId('ops-managers'),
  eva: byId('ops-eva-cards'),
  billing: byId('facturability-summary'),
  capacity: byId('ops-capacity'),
  service: /** @type {HTMLSelectElement} */ (byId('ops-service')),
  client: /** @type {HTMLSelectElement} */ (byId('ops-client')),
};

/** Ultimo corte combinado de la API; null mientras llega el primero. @type {any} */
let view = null;
let billing = { restricted: false, data: null, failed: false };
let run = 0; // cada carga nueva invalida las respuestas de la anterior
let refreshing = false;
/** @type {Set<AbortController>} */
const controllers = new Set();

const filters = () => ({ servicio: readParams().get('servicio') || '', cuenta: readParams().get('cuenta') || '' });

function abortAll() {
  controllers.forEach((controller) => controller.abort());
  controllers.clear();
}

/**
 * @param {string} path
 * @param {Record<string, unknown>} params
 * @param {boolean} [filtered] false cuando la cifra no depende de Servicio ni Cuenta.
 */
async function get(path, params, filtered = true) {
  const controller = new AbortController();
  controllers.add(controller);
  try {
    return await apiGet(path, { ...(filtered ? filters() : {}), ...params }, { signal: controller.signal, timeout: 120000 });
  } finally {
    controllers.delete(controller);
  }
}

/** @param {string} text */
const status = (text) => {
  regions.status.textContent = text;
  regions.refresh.title = text;
};
/** @param {boolean} value */
function busy(value) {
  regions.refresh.disabled = value;
  regions.refresh.textContent = value ? 'Actualizando…' : 'Actualizar datos';
}

// ---------- Pintar ----------

function renderAlerts() {
  const messages = [];
  if (view.source_errors.length) {
    const lead = view.stale ? 'No se pudo renovar el corte guardado.' : 'Información parcial del portafolio.';
    messages.push(el('div', { class: 'ops-warning', role: 'status', text: `${lead} ${view.source_errors.join(' ')}` }));
  }
  if (view.error) {
    messages.push(el('div', { class: 'err', text: `No se pudo leer Google Sheets: ${view.error} Las cifras reales aparecerán cuando la conexión responda.` }));
  }
  regions.alerts.replaceChildren(...messages);
}

/** @param {HTMLSelectElement} select @param {string[]} options @param {string} selected @param {string} all */
function fillSelect(select, options, selected, all) {
  const names = selected && !options.includes(selected) ? [selected, ...options] : options;
  select.replaceChildren(
    el('option', { value: '', text: all }),
    ...names.map((name) => el('option', { value: name, text: name })),
  );
  select.value = selected;
}

function renderFilters() {
  const { service, client } = view.filters;
  fillSelect(regions.service, view.options.services, service, 'Todos los servicios');
  fillSelect(regions.client, view.options.clients, client, 'Todas las cuentas');
}

function renderAll() {
  renderAlerts();
  renderFilters();
  regions.cut.textContent = view.loaded_at ? `Corte calculado al ${formatDateTime(view.loaded_at, ', ')}` : '';
  renderMetrics(regions.metrics, view);
  renderHealth(regions.health, view);
  renderManagers(regions.managers, view, urls);
  renderEva(regions.eva, view, urls);
  renderCapacity(regions.capacity, view.capacity);
  renderBilling(regions.billing, { ...billing, restricted: view.restricted });
}

// ---------- Mezclar respuestas ----------

/** La base trae todo, salvo lo que decide el primer corte. @param {any} next */
function mergeBase(next) {
  view = { ...next, pending_blocks: view.pending_blocks, async: view.async, billing_fresh: view.billing_fresh };
}

/**
 * Cada bloque actualiza solo lo suyo; otro bloque pudo llegar antes.
 * @param {string} block
 * @param {any} data
 */
function applyBlock(block, data) {
  const bySlug = new Map(data.managers.map((/** @type {any} */ m) => [m.slug, m]));
  if (block === 'eva4') view.eva.eva4 = data.eva.eva4;
  if (block === 'capacidad') view.capacity = data.capacity;
  if (block === 'inversion') {
    view.investment = data.investment;
    for (const manager of view.managers) manager.investment = bySlug.get(manager.slug)?.investment ?? manager.investment;
  }
  if (block === 'eva3') {
    const previous = new Map(view.managers.map((/** @type {any} */ m) => [m.slug, m]));
    view.managers = data.managers.map((/** @type {any} */ m) => {
      const old = previous.get(m.slug);
      // La inversion pudo llegar antes que este bloque: no se pierde.
      return !m.investment.ready && old?.investment.ready ? { ...m, investment: old.investment } : m;
    });
    Object.assign(view, {
      summary: data.summary,
      service_distribution: data.service_distribution,
      portfolio_total: data.portfolio_total,
      health_states: data.health_states,
      consumption_pending: data.consumption_pending,
      has_projects: data.has_projects,
    });
    view.eva.eva1 = data.eva.eva1;
    view.eva.eva3 = data.eva.eva3;
  }
}

// ---------- Cargar ----------

const BLOCKS = /** @type {const} */ ([
  ['eva4', 'EVA-04 Report'],
  ['inversion', 'inversión'],
  ['capacidad', 'capacidad'],
  ['eva3', 'EVA 3'],
]);

/**
 * @param {string[]} failures
 * @param {boolean} force
 * @param {number} mine
 */
async function refreshPortfolio(failures, force, mine) {
  try {
    const extra = force ? { actualizar: 1 } : {};
    const base = await get('screens/operativa/datos/', extra);
    if (mine !== run) return;
    mergeBase(base.data);
    renderAll();
    busy(true);
    if (base.data.source_errors.length) failures.push('fuentes del portafolio');
    status('Proyectos y estados disponibles. Actualizando consumo, inversión y capacidad…');
    const needed = force ? null : view.pending_blocks;
    await Promise.all(
      BLOCKS.filter(([block]) => !needed || needed.includes(block)).map(async ([block, label]) => {
        try {
          const answer = await get('screens/operativa/datos/', { ...extra, bloque: block });
          if (mine !== run) return;
          // Un bloque incompleto no reemplaza lo que ya se muestra.
          if (answer.data.block_error) throw new Error('Datos parciales');
          applyBlock(block, answer.data);
          renderAll();
        } catch (error) {
          if (mine === run) failures.push(label);
        }
      }),
    );
  } catch (error) {
    if (mine === run) failures.push('portafolio');
  }
}

/** @param {boolean} force */
async function refreshBilling(force) {
  const mine = run;
  regions.billing.setAttribute('aria-busy', 'true');
  try {
    const answer = await get('screens/operativa/facturabilidad/', force ? { actualizar: 1 } : {}, false);
    if (mine !== run) return;
    billing = { restricted: false, data: answer.data, failed: false };
    renderBilling(regions.billing, { ...billing, restricted: false });
    if (answer.data.partial) throw new Error('Datos parciales');
  } catch (error) {
    if (mine === run && !billing.data) {
      billing = { ...billing, failed: true };
      renderBilling(regions.billing, { ...billing, restricted: view.restricted });
    }
    throw error;
  } finally {
    if (mine === run) regions.billing.setAttribute('aria-busy', 'false');
  }
}

/** @param {boolean} [force] */
async function refresh(force = false) {
  if (refreshing) return;
  refreshing = true;
  const mine = run;
  busy(true);
  status('Actualizando indicadores. Puedes seguir consultando el corte disponible…');
  /** @type {string[]} */
  const failures = [];
  try {
    const wantsBilling = !view.restricted && (force || !view.billing_fresh);
    await Promise.all([
      refreshPortfolio(failures, force, mine),
      wantsBilling ? refreshBilling(force).catch(() => failures.push('facturabilidad')) : null,
    ]);
    if (mine !== run) return;
    status(
      failures.length
        ? `Actualización parcial: no se pudo actualizar ${failures.join(', ')}. Se conserva la información disponible. Puedes reintentar.`
        : 'Consulta completada. Cada sección indica su período; los datos pueden proceder de caché.',
    );
  } finally {
    if (mine === run) {
      refreshing = false;
      busy(false);
    }
  }
}

async function start() {
  abortAll();
  run += 1;
  const mine = run;
  refreshing = false;
  billing = { restricted: false, data: null, failed: false };
  busy(true);
  status('Calculando indicadores…');
  try {
    const answer = await get('screens/operativa/', {});
    if (mine !== run) return;
    view = answer.data;
    // El ultimo corte de facturabilidad se pinta ya; abajo se decide si se renueva.
    if (view.billing) billing = { restricted: false, data: view.billing, failed: false };
    renderAll();
  } catch (error) {
    if (mine !== run) return;
    busy(false);
    status('');
    regions.alerts.replaceChildren(
      el(
        'div',
        { class: 'err', role: 'alert' },
        error instanceof Error ? error.message : 'No se pudo cargar Operativa.',
        el('button', { type: 'button', class: 'btn btn-ghost', onclick: start, text: 'Reintentar' }),
      ),
    );
    return;
  }
  if (view.async) await refresh(false);
  else {
    busy(false);
    status('');
    if (!view.restricted && !view.billing_fresh) {
      refreshBilling(false).catch(() => status('No se pudo completar facturabilidad. Consulta el detalle.'));
    }
  }
}

// ---------- Eventos ----------

regions.refresh.addEventListener('click', () => refresh(true));

regions.service.addEventListener('change', () => {
  writeParams({ servicio: regions.service.value || null }, { push: true });
  start();
});

regions.client.addEventListener('change', () => {
  const name = regions.client.value;
  if (!name) {
    writeParams({ cuenta: null }, { push: true });
    start();
    return;
  }
  location.assign(`${urls.account.replace('account-placeholder', slugify(name))}?nombre=${encodeURIComponent(name)}`);
});

addEventListener('popstate', start);
addEventListener('pagehide', abortAll);

start();
