// @ts-check
// Comercial: las cifras y tablas llegan en la plantilla; aqui solo el
// comportamiento (filas extra, desplegables, año de referencia y el detalle).
import { el } from '#app/lib/dom.js';
import { formatCompact } from '#app/lib/format.js';
import { watchLoadingMessages } from '#app/ui/portal-loading.js';

watchLoadingMessages();

const PIPELINE = '#commercial-pipeline';
const FIELDS = [
  ['factura', 'Factura'],
  ['monto', 'Valor original'],
  ['moneda', 'Moneda'],
  ['duracion', 'Duracion del servicio'],
  ['account', 'Account'],
  ['fechaInicio', 'Fecha inicio'],
  ['stageComercial', 'Stage comercial'],
  ['cio', 'CIO'],
  ['calculadora', 'Calculadora'],
  ['arq', 'Arquitectura'],
  ['enTiempo', 'En tiempo'],
  ['observaciones', 'Observaciones'],
  ['estimacion', 'Estimacion'],
  ['seguimiento', 'Ultimo seguimiento'],
];
/** @param {unknown} value */
const number = (value) => (value === null || value === undefined ? 'Sin dato' : Number(value).toLocaleString('es-MX', { maximumFractionDigits: 2 }));
/** @param {unknown} value */
const text = (value) => String(value ?? 'Sin dato');

// Ancho de las barras de etapa: el servidor entrega el porcentaje.
document.querySelectorAll('[data-width]').forEach((node) => {
  /** @type {HTMLElement} */ (node).style.width = `${/** @type {HTMLElement} */ (node).dataset.width}%`;
});

// Cada servicio abre el detalle de sus cuentas.
document.querySelectorAll('.service-accounts').forEach((node) => {
  const details = /** @type {HTMLDetailsElement} */ (node);
  details.addEventListener('toggle', () => {
    const row = /** @type {HTMLElement} */ (/** @type {HTMLElement} */ (details.closest('tr')).nextElementSibling);
    row.hidden = !details.open;
  });
});

// El año de referencia recarga la pagina con el año elegido.
for (const id of ['pipeline-year', 'banner-year']) {
  document.getElementById(id)?.addEventListener('change', (event) => {
    const url = new URL(location.href);
    url.searchParams.set('pipeline_year', /** @type {HTMLSelectElement} */ (event.target).value);
    url.hash = PIPELINE;
    location.assign(url.href);
  });
}

/** «Ver más» / «Ver menos» de las listas de etapas y cuentas. @param {string} selector @param {string} extra */
function foldable(selector, extra) {
  const button = document.querySelector(selector);
  button?.addEventListener('click', () => {
    const expanded = button.getAttribute('aria-expanded') !== 'true';
    /** @type {HTMLElement} */ (button.closest('.card')).querySelectorAll(extra).forEach((row) => {
      /** @type {HTMLElement} */ (row).hidden = !expanded;
    });
    button.setAttribute('aria-expanded', String(expanded));
    button.textContent = expanded ? 'Ver menos ↑' : 'Ver más ↓';
  });
}
foldable('.stage-toggle', '[data-extra-stage]');
foldable('.account-toggle', '[data-extra-account]');

// Detalle de las oportunidades de un grupo (cuenta y servicio).
const modal = /** @type {HTMLDialogElement | null} */ (document.getElementById('pipeline-detail-dialog'));
const source = document.getElementById('pipeline-detail-data');
if (modal && source) {
  const data = JSON.parse(source.textContent || '{}');
  document.addEventListener('click', (event) => {
    const button = /** @type {HTMLElement | null} */ (/** @type {Element} */ (event.target).closest('[data-pipeline-detail]'));
    const group = button && data[/** @type {string} */ (button.dataset.pipelineDetail)];
    if (!group) return;
    /** @type {HTMLElement} */ (document.getElementById('pipeline-detail-title')).textContent = `${group.account} | ${group.service}`;
    /** @type {HTMLElement} */ (document.getElementById('pipeline-detail-subtitle')).textContent = `${group.title} · ${group.rows.length} registros · ${number(group.total)} h`;
    /** @type {HTMLElement} */ (document.getElementById('pipeline-detail-rows')).replaceChildren(
      ...group.rows.map((/** @type {any} */ row) =>
        el(
          'tr',
          {},
          ...[row.cuenta, row.oportunidad, row.manager].map((value) => el('td', { text: text(value || 'Sin dato') })),
          el('td', {}, el('span', { class: 'live-status', text: text(row.etapa) })),
          el('td', { text: text(row.fechaCierre) }),
          el('td', { text: text(row.servicio) }),
          el('td', { text: number(row.horas) }),
          el('td', { text: formatCompact(row.usd) }),
          el('td', { text: (row.probabilidad === null || row.probabilidad === undefined ? 'Pendiente' : `${number(row.probabilidad)}%`) + (row.probabilidadFicticia ? ' (ficticia)' : '') }),
          el(
            'td',
            {},
            el(
              'details',
              {},
              el('summary', { text: 'Ver datos A–U' }),
              el('dl', {}, ...FIELDS.flatMap(([key, label]) => [el('dt', { text: label }), el('dd', { text: text(row[key]) })])),
            ),
          ),
        ),
      ),
    );
    modal.showModal();
  });
  modal.querySelector('.pipeline-dialog-close')?.addEventListener('click', () => modal.close());
  modal.addEventListener('click', (event) => {
    if (event.target !== modal) return;
    const box = modal.getBoundingClientRect();
    const { clientX: x, clientY: y } = /** @type {MouseEvent} */ (event);
    if (x < box.left || x > box.right || y < box.top || y > box.bottom) modal.close();
  });
}
