// @ts-check
// Business Overview: el ultimo corte preparado, sin consultar las fuentes.
import { apiGet } from '#app/data/api-client.js';
import { formatDateTime } from '#app/lib/format.js';
import { createAgreements } from '#app/ui/agreements.js';
import { mountDateRangePicker } from '#app/ui/date-range-picker.js';
import { watchLoadingMessages } from '#app/ui/portal-loading.js';
import { mountCut } from './sections/cut.js';
import { mountMethods } from './sections/methods.js';
import { renderMetrics } from './sections/metrics.js';
import { mountRankings } from './sections/rankings.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const form = /** @type {HTMLFormElement} */ (byId('executive-period-form'));
const { accountUrl = '', query = '' } = byId('executive-page-data').dataset;

/** Los filtros de periodo de la URL, para la API. */
function period() {
  /** @type {Record<string, string>} */
  const out = {};
  const params = new URLSearchParams(location.search);
  for (const key of ['periodo', 'anio', 'trimestre', 'mes', 'desde', 'hasta']) {
    const value = params.get(key);
    if (value) out[key] = value;
  }
  return out;
}

/** Destino de una cuenta, con el periodo elegido. @param {any} account */
const accountHref = (account) =>
  `${accountUrl.replace('account-placeholder', encodeURIComponent(account.slug))}?nombre=${encodeURIComponent(account.name)}${query ? `&${query}` : ''}`;

mountDateRangePicker(/** @type {HTMLDetailsElement} */ (byId('executive-date-picker')), form);
mountMethods();
watchLoadingMessages();
byId('revenue-cost-open').addEventListener('click', () => {
  const url = new URL(/** @type {string} */ (byId('revenue-cost-open').dataset.url), location.href);
  url.search = location.search;
  location.assign(url.toString());
});

async function start() {
  const params = period();
  let body;
  try {
    body = await apiGet('screens/executive/', params);
  } catch (error) {
    byId('executive-cut-status').textContent = error instanceof Error ? error.message : 'No se pudo consultar el corte.';
    mountRankings(null, accountHref);
    return;
  }
  const { data, meta } = body;
  const model = {
    revenue: data.finance?.revenue ?? null,
    costs: data.finance?.costs ?? null,
    operations: data.operations || {},
    commercial: data.commercial ?? null,
    monthly: data.monthly ?? null,
    loadedAt: meta.loaded_at,
  };
  byId('portal-freshness-text').textContent = meta.loaded_at ? `Datos al ${formatDateTime(meta.loaded_at, ', ')}` : 'Sin fecha de actualización';
  const loading = renderMetrics(model);
  mountRankings(data.accounts, accountHref);
  mountCut({ model, loading, period: params });
  const names = (data.accounts || []).map((/** @type {any} */ a) => a.name).sort((/** @type {string} */ a, /** @type {string} */ b) => a.localeCompare(b, 'es'));
  byId('executive-agreements-slot').replaceWith(createAgreements({ accounts: names }));
}

start();
