// @ts-check
// Personas, bandas y tarifas de un Project ID; se consultan al abrir el desglose.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { formatMoney, formatNumber } from '#app/lib/format.js';

const PENDING = 'Pendiente';
const HEADERS = ['Persona', 'Horas', 'Banda', 'Mes de banda', 'Tarifa interna de banda (USD/h)', 'Costo', 'Estado'];

/** @param {number | null | undefined} value */
const rate = (value) =>
  value === null || value === undefined ? PENDING : `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** @param {any} person */
function personRow(person) {
  const state = person.missing ? 'Falta banda o tarifa' : 'Horas × tarifa';
  const cells = [
    person.name,
    person.hours == null ? PENDING : formatNumber(person.hours),
    person.band ?? PENDING,
    person.band_month ?? PENDING,
    rate(person.rate),
    formatMoney(person.cost),
  ];
  return el(
    'tr',
    {},
    ...cells.map((text) => el('td', { text })),
    el('td', {}, el('span', { class: `person-cost-state${person.missing ? ' missing' : ''}`, text: state })),
  );
}

/** @param {any} group */
function groupTable(group) {
  const people = group.people || [];
  return el(
    'div',
    {},
    el('h4', { text: group.label }),
    people.length
      ? el(
          'div',
          { class: 'mg-scroll' },
          el(
            'table',
            {},
            el('thead', {}, el('tr', {}, ...HEADERS.map((title) => el('th', { scope: 'col', text: title })))),
            el('tbody', {}, ...people.map(personRow)),
          ),
        )
      : el('p', { text: 'Sin registros disponibles para este ID y periodo.' }),
  );
}

/**
 * Fabrica el desglose de un proyecto: carga una sola vez, al abrirse.
 * @param {string} projectId
 * @param {string} account
 * @param {() => Record<string, string>} periodParams
 */
export function peopleDetails(projectId, account, periodParams) {
  const content = el('div', { class: 'mg-people-content', text: 'Abre para consultar el desglose.' });
  const details = /** @type {HTMLDetailsElement} */ (
    el('details', { class: 'mg-people', dataset: { project: projectId } }, el('summary', { text: 'Ver personas y tarifas' }), content)
  );
  let loaded = false;
  let busy = false;
  details.addEventListener('toggle', async () => {
    if (!details.open || loaded || busy) return;
    busy = true;
    content.textContent = 'Consultando personas y tarifas…';
    try {
      const body = await apiGet('costs/project/', { ...periodParams(), id: projectId, nombre: account });
      const data = body.data;
      const grouped = (data.sprints || []).some((/** @type {any} */ g) => /^(S[0-9]|CR)/i.test(g.label));
      const groups = grouped ? data.sprints : [{ label: 'Personas', people: data.people || [] }];
      content.replaceChildren(
        el('p', { text: `Clockify: ${data.id} · ${data.scope_start || ''} a ${data.scope_end || ''}` }),
        ...groups.map(groupTable),
      );
      loaded = true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No se pudo consultar el detalle';
      content.textContent = `${message} · Cierra y abre para reintentar.`;
    } finally {
      busy = false;
    }
  });
  return details;
}
