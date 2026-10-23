// @ts-check
// Detalle de costos por proyecto: resumen del corte, tabla con filtros y
// desglose de personas y tarifas bajo demanda.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { watchLoadingMessages } from '#app/ui/portal-loading.js';
import { renderDetail } from './sections/details.js';
import { fmt, marginColor, marginText, money } from './sections/format.js';

watchLoadingMessages();
/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const { account = '', projectUrl = '' } = byId('cost-page-data').dataset;
const body = byId('cost-audit-body');
const search = /** @type {HTMLInputElement} */ (byId('cost-search'));
const filter = /** @type {HTMLSelectElement} */ (byId('cost-filter'));
const SIZE = 10;
const PERIOD_KEYS = ['periodo', 'anio', 'trimestre', 'mes', 'desde', 'hasta'];
/** @type {any[]} */
let rows = [];
let page = 1;
/** @type {Record<string, any>} */
let preparedDetails = {};
/** @type {ReturnType<typeof setInterval> | null} */
let preparationTimer = null;

/** El periodo de la URL, solo si se eligio uno. */
function period() {
  /** @type {Record<string, string>} */
  const out = {};
  const params = new URLSearchParams(location.search);
  if (!params.has('periodo')) return out;
  for (const key of PERIOD_KEYS) if (params.has(key)) out[key] = /** @type {string} */ (params.get(key));
  return out;
}
/** @param {string} path @param {Record<string, string>} [extra] */
const get = async (path, extra = {}) => (await apiGet(path, { ...(account ? { nombre: account } : {}), ...period(), ...extra })).data;

/** @param {string} id */
function projectLink(id) {
  const target = new URL(projectUrl.replace('project-placeholder', encodeURIComponent(id)), location.href);
  target.searchParams.set('volver', location.pathname + location.search);
  return target.pathname + target.search;
}

/** @param {any} p */
function projectCell(p) {
  if (p.future) return el('span', { text: p.id });
  if (p.cost !== null && p.cost !== undefined && !p.error) return el('a', { class: 'cost-project-link', href: projectLink(p.id), 'aria-label': `Ver proyecto ${p.id}`, text: p.id });
  return el('button', { type: 'button', class: 'cost-project-unavailable', 'data-project-unavailable': p.id, 'data-project-error': p.error || 'La consulta de este proyecto está pendiente.', text: p.id });
}

/** @param {any} p */
function statePill(p) {
  const kind = p.future ? 'future' : p.cost === null || p.cost === undefined ? 'error' : p.complete ? '' : 'partial';
  const label = p.future ? 'Futuro' : p.cost === null || p.cost === undefined ? 'Sin consultar / error' : p.complete ? (p.hours === 0 ? 'Sin horas en el periodo' : 'Calculado') : 'Costo parcial';
  const note = !p.complete && !p.future ? [el('small', { class: 'audit-error', text: p.cost === null || p.cost === undefined ? p.error || 'Pendiente de consultar Clockify' : 'Falta banda o tarifa' })] : [];
  return [el('span', { class: `audit-pill ${kind}`.trim(), text: label }), ...note];
}

/** @param {any} p */
function projectRow(p) {
  const margin = el('td', { class: 'cost-number', title: p.margin_provisional ? 'Margen provisional: costos incompletos' : 'Margen = (revenue − costo) ÷ revenue', text: p.future ? '—' : marginText(p) });
  margin.style.fontWeight = '700';
  margin.style.color = marginColor(p);
  return [
    el(
      'tr',
      {},
      el('td', { class: 'project-id' }, projectCell(p)),
      el('td', { class: 'cost-number', text: p.future ? '—' : fmt(p.hours) }),
      el('td', { class: 'cost-number', text: p.future ? '—' : p.cost === null || p.cost === undefined ? 'Pendiente' : money(p.cost) }),
      el('td', { class: 'cost-number', text: p.revenue === null || p.revenue === undefined ? 'Sin datos' : money(p.revenue) }),
      margin,
      el('td', {}, ...statePill(p)),
      el('td', {}, el('button', { type: 'button', 'data-persons': p.id, disabled: p.future || null, text: 'Ver personas y tarifas' })),
    ),
    el('tr', { class: 'audit-detail-row', hidden: true }, el('td', { colspan: 7 }, el('div', { class: 'audit-detail' }))),
  ];
}

function render() {
  const wanted = search.value.toLowerCase();
  const state = filter.value;
  const filtered = rows.filter(
    (p) =>
      p.id.toLowerCase().includes(wanted) &&
      (state === 'all' || (state === 'future' && p.future) || (state === 'pending' && p.cost == null && !p.future) || (state === 'complete' && p.cost != null && p.complete) || (state === 'partial' && p.cost != null && !p.complete)),
  );
  page = Math.min(page, Math.max(1, Math.ceil(filtered.length / SIZE)));
  body.replaceChildren(...filtered.slice((page - 1) * SIZE, page * SIZE).flatMap(projectRow));
  byId('cost-page-label').textContent = `Mostrando ${filtered.length ? (page - 1) * SIZE + 1 : 0}–${Math.min(page * SIZE, filtered.length)} de ${filtered.length}`;
  /** @type {HTMLButtonElement} */ (byId('cost-prev')).disabled = page === 1;
  /** @type {HTMLButtonElement} */ (byId('cost-next')).disabled = page * SIZE >= filtered.length;
}

/** El resumen global con el corte actual. @param {any} data */
function summary(data) {
  const consulted = data.consulted ?? rows.length - data.pending - (data.future || 0);
  byId('cost-summary-label').textContent = data.complete ? 'COSTO GLOBAL' : 'COSTO PARCIAL CALCULADO';
  byId('cost-total').textContent = money(data.cost);
  byId('cost-consulted').textContent = `${consulted} de ${rows.length}`;
  byId('cost-pending').textContent = data.pending;
  byId('cost-entries').textContent = fmt(data.deduplicated_entries);
  return consulted;
}

/** @param {boolean} [force] */
async function refresh(force = false) {
  try {
    const data = await get('costs/summary/', force ? { actualizar: '1' } : {});
    rows = data.projects;
    preparedDetails = data.prepared_details || {};
    if (data.preparing && !preparationTimer) {
      preparationTimer = setInterval(async () => {
        try {
          const state = (await apiGet('screens/executive/actualizar/', period())).data;
          if (state.state === 'ready' || state.state === 'failed') {
            if (preparationTimer) clearInterval(preparationTimer);
            preparationTimer = null;
            await refresh(true);
          }
        } catch (_) {
          if (preparationTimer) clearInterval(preparationTimer);
          preparationTimer = null;
          byId('cost-note').textContent = 'No se completó la preparación automática. Se conserva el corte disponible.';
        }
      }, 5000);
    }
    const consulted = summary(data);
    byId('cost-updated').textContent = `Hoy, ${new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}`;
    byId('cost-note').textContent = `${consulted} de ${rows.length} proyectos consultados · ${data.pending} pendientes · banda ${data.band_month} · ${data.deduplicated_entries} registros unicos · cache de costos 24 h`;
    render();
  } catch (error) {
    byId('cost-total').textContent = error instanceof Error ? error.message : 'No se pudo consultar';
  }
}

/** Actualiza la fila de un proyecto con su desglose recien consultado. @param {HTMLTableRowElement} row @param {any} data */
function updateRow(row, data) {
  const index = rows.findIndex((p) => p.id.toLowerCase() === String(data.id).toLowerCase());
  if (index === -1) return;
  rows[index] = { ...rows[index], ...data, error: data.error || '' };
  const p = rows[index];
  const [id, hours, cost, revenue, margin, state] = row.cells;
  id.replaceChildren(projectCell(p));
  hours.textContent = fmt(p.hours);
  cost.textContent = p.cost === null || p.cost === undefined ? 'Pendiente' : money(p.cost);
  revenue.textContent = p.revenue === null || p.revenue === undefined ? 'Sin datos' : money(p.revenue);
  margin.textContent = marginText({ ...p, margin_provisional: !p.complete });
  margin.style.color = marginColor(p);
  margin.title = p.complete ? 'Margen = (revenue − costo) ÷ revenue' : 'Margen provisional: costos incompletos';
  const kind = p.cost === null || p.cost === undefined ? 'error' : p.complete ? '' : 'partial';
  state.replaceChildren(
    el('span', { class: `audit-pill ${kind}`.trim(), text: p.cost === null || p.cost === undefined ? 'Sin consultar / error' : p.complete ? 'Calculado' : 'Costo parcial' }),
    ...(!p.complete ? [el('small', { class: 'audit-error', text: `Falta banda o tarifa · ${fmt(p.missing_hours || 0)} h pendientes de costear` })] : []),
  );
}

body.addEventListener('click', async (event) => {
  const unavailable = /** @type {HTMLElement | null} */ (/** @type {Element} */ (event.target).closest('[data-project-unavailable]'));
  if (unavailable) {
    const notice = byId('cost-project-notice');
    notice.textContent = `No es posible abrir el proyecto ${unavailable.dataset.projectUnavailable}. ${unavailable.dataset.projectError}`;
    notice.hidden = false;
    notice.scrollIntoView({ block: 'nearest' });
    return;
  }
  const button = /** @type {HTMLButtonElement | null} */ (/** @type {Element} */ (event.target).closest('[data-persons]'));
  if (!button) return;
  const row = /** @type {HTMLTableRowElement} */ (button.closest('tr'));
  const detail = /** @type {HTMLElement} */ (row.nextElementSibling);
  const target = /** @type {HTMLElement} */ (detail.querySelector('.audit-detail'));
  if (!detail.hidden) {
    detail.hidden = true;
    button.textContent = 'Ver personas y tarifas';
    return;
  }
  detail.hidden = false;
  button.textContent = 'Ocultar detalle';
  if (target.dataset.loaded === 'true') return;
  target.textContent = 'Consultando...';
  button.disabled = true;
  try {
    const prepared = preparedDetails[String(button.dataset.persons).toLowerCase()];
    const data = prepared || (await get('costs/project/', { id: /** @type {string} */ (button.dataset.persons) }));
    preparedDetails[String(data.id).toLowerCase()] = data;
    target.dataset.loaded = 'true';
    updateRow(row, data);
    target.replaceChildren(...renderDetail(data));
    if (!data.people.length) target.textContent = 'No hay horas en Clockify para el periodo seleccionado.';
    if (!prepared) {
      try {
        const all = await get('costs/summary/');
        const consulted = all.projects.length - all.pending;
        summary({ ...all, consulted });
        byId('cost-note').textContent = `${consulted} de ${all.projects.length} proyectos consultados · ${all.pending} pendientes · Incluye los costos parciales disponibles.`;
      } catch (_) {
        byId('cost-note').textContent = 'Detalle actualizado. No se pudo actualizar el total; pulsa Actualizar resumen.';
      }
    }
  } catch (error) {
    target.textContent = error instanceof Error ? error.message : 'No se pudo consultar';
  } finally {
    button.disabled = false;
  }
});

byId('cost-prev').addEventListener('click', () => {
  page -= 1;
  render();
});
byId('cost-next').addEventListener('click', () => {
  page += 1;
  render();
});
for (const control of [search, filter]) {
  control.addEventListener('input', () => {
    page = 1;
    render();
  });
}
byId('cost-refresh').addEventListener('click', () => refresh(false));
refresh();
