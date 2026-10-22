// @ts-check
// Business Overview: pide el corte preparado a la API, dibuja tarjetas,
// rentabilidad mensual, comparacion de cuentas y acuerdos, y pregunta si ya
// llegaron los bloques que faltaban.
import { apiGet, apiSend } from '#app/data/api-client.js';
import { readParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatDateTime } from '#app/lib/format.js';
import { mountAgreements } from '#app/ui/agreements.js';
import { mountGlossary } from '#app/ui/glossary.js';
import { mountMonthlyChart } from '#app/ui/monthly-chart.js';
import { mountPeriodPicker } from '#app/ui/period-picker.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';
import { renderAccounts } from './sections/accounts.js';
import { commercialCard, financeCard, operationsCard } from './sections/cards.js';
import { openMethod } from './sections/methods.js';

const POLL_MS = 5000;
const PERIOD_KEYS = ['periodo', 'anio', 'mes', 'trimestre', 'desde', 'hasta'];

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const root = byId('exec-root');
const cards = byId('exec-cards');
const monthly = byId('exec-monthly');
const status = byId('exec-status');
const refresh = /** @type {HTMLButtonElement} */ (byId('exec-refresh'));
const errorBox = byId('exec-error');
const urls = /** @type {Record<string, string>} */ (root.dataset);

const params = readParams();
const period = Object.fromEntries(PERIOD_KEYS.filter((k) => params.has(k)).map((k) => [k, /** @type {string} */ (params.get(k))]));

/** @type {any} */
let reference = null;
/** @type {ReturnType<typeof setInterval> | null} */
let timer = null;
let agreementsMounted = false;

mountPeriodPicker(byId('exec-period'), { label: urls.label, start: urls.start, end: urls.end });

/** @param {string} group */
const info = (group) => reference && openMethod(reference, group, urls.dictionaryUrl);

/** @param {any} body */
function render(body) {
  const { data, meta } = body;
  errorBox.replaceChildren();
  clearState(cards);
  cards.replaceChildren(
    financeCard(data, meta, { year: urls.year, costsUrl: urls.costsUrl, info }),
    operationsCard(data, meta, { operationsUrl: urls.operationsUrl, info }),
    commercialCard(data, meta, { commercialUrl: urls.commercialUrl, info }),
  );

  const profitability = data.monthly;
  if (profitability) {
    const months = (profitability.months || []).map((/** @type {any} */ row) => ({
      ...row,
      margin: row.cost != null && Number(row.revenue) > 0 ? ((Number(row.revenue) - Number(row.cost)) / Number(row.revenue)) * 100 : null,
    }));
    const holder = el('div', { class: 'monthly-chart' });
    monthly.replaceChildren(
      el(
        'div',
        { class: 'monthly-title' },
        el('h3', { text: `Rentabilidad mensual · ${urls.year}` }),
        el('span', { class: 'badge', text: profitability.complete ? 'Corte preparado' : 'Margen parcial · costos disponibles' }),
        el('div', { class: 'legend' }, el('span', { class: 'rev', text: '● Facturación' }), el('span', { class: 'cost', text: '● Costos' }), el('span', { class: 'mar', text: '● Margen bruto (%)' })),
      ),
      holder,
      el(
        'details',
        {},
        el('summary', { text: 'Fuentes y cálculo' }),
        el('p', {
          class: 'note',
          text: 'Facturación mensual = Invoiced + Collected (incluido factoring), por mes de DataRevenue G; no usa el monto total del proyecto. Costos por fecha de cada registro de Clockify. Fechas y conceptos de facturación pendientes de validar con Florencia. La línea muestra el margen con los costos disponibles; * indica un margen parcial que puede cambiar al completar costos.',
        }),
      ),
    );
    mountMonthlyChart(holder, { months, complete: profitability.complete });
  } else {
    monthly.replaceChildren(
      el('h3', { text: `Rentabilidad mensual · ${urls.year}` }),
      el('p', { class: 'note', text: meta.scope === 'limited' ? 'Cifra del portafolio completo; no disponible para tu alcance.' : 'El corte del periodo se está preparando. Las cifras no se actualizarán automáticamente.' }),
    );
  }

  renderAccounts(byId('exec-accounts'), data.accounts, { accountUrl: urls.accountUrl, label: urls.label, allAccountsUrl: urls.allAccountsUrl });
  if (!agreementsMounted) {
    agreementsMounted = true;
    mountAgreements(byId('exec-agreements'), { accounts: (data.accounts || []).map((/** @type {any} */ a) => a.name) });
  }

  const loaded = formatDateTime(meta.loaded_at);
  status.textContent = loaded ? `Última consulta: ${loaded}` : 'Consultando datos del periodo…';
  const missing = !meta.blocks.financial || !meta.blocks.operations || !meta.blocks.commercial;
  if (missing && meta.scope !== 'limited') watch();
}

function stop() {
  if (timer) clearInterval(timer);
  timer = null;
  refresh.disabled = false;
}

/** Cada 5 s pregunta si el servidor ya preparo algo; entonces vuelve a pedir el corte. */
function watch() {
  if (timer) return;
  timer = setInterval(async () => {
    try {
      const { data } = await apiGet('screens/executive/actualizar/', period);
      if (data.state === 'ready' || data.blocks.financial) {
        stop();
        if (data.state === 'ready' && !data.blocks.financial) {
          status.textContent = 'No se pudo completar la consulta financiera. Pulsa Actualizar datos para reintentar; no se mostrarán cifras inventadas.';
        } else {
          load(false);
        }
      } else if (data.state === 'failed') {
        stop();
        status.textContent = 'No se pudo completar. Se conserva el corte mostrado.';
      } else if (data.state === 'running' || data.state === 'queued') {
        status.textContent = 'Preparando en segundo plano. Se conserva el corte mostrado.';
      }
    } catch (_) {
      stop();
      status.textContent = 'Sin conexión para actualizar. Se conserva el corte mostrado.';
    }
  }, POLL_MS);
}

refresh.addEventListener('click', async () => {
  refresh.disabled = true;
  status.textContent = 'Consultando fuentes en segundo plano…';
  try {
    await apiSend('POST', `screens/executive/actualizar/?${new URLSearchParams(period)}`);
    watch();
  } catch (_) {
    refresh.disabled = false;
    status.textContent = 'No se pudo iniciar la actualización.';
  }
});

/** @param {boolean} first */
async function load(first = true) {
  if (first) showLoading(cards, 'Consultando el corte…');
  try {
    const [body, ref] = await Promise.all([apiGet('screens/executive/', period), reference ? Promise.resolve(null) : apiGet('reference/glossary/')]);
    if (ref) {
      reference = ref.data;
      mountGlossary(byId('exec-glossary'), reference.groups, urls.dictionaryUrl);
    }
    render(body);
  } catch (error) {
    showError(cards, error, { onRetry: () => load(true) });
  }
}

load();
