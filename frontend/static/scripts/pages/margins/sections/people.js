// @ts-check
// Personas, bandas y tarifas de un Project ID; se piden al abrir el detalle.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { formatMoney, formatNumber } from '#app/lib/format.js';

const PENDING = 'Pendiente';
const text = (/** @type {unknown} */ value) => (value === null || value === undefined ? PENDING : String(value));
const rate = (/** @type {number | null} */ value) =>
  value === null || value === undefined
    ? PENDING
    : `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const hours = (/** @type {number | null} */ value) => (value === null || value === undefined ? PENDING : formatNumber(value));

/** @param {any} person */
function personRow(person) {
  const cost = person.missing
    ? person.cost > 0 ? `${formatMoney(person.cost)}*` : PENDING
    : formatMoney(person.cost);
  const personRate = person.missing && !(person.rate > 0) ? PENDING : rate(person.rate);
  const state = el('span', {
    class: `person-cost-state${person.missing ? ' missing' : ''}`,
    text: person.missing ? 'Falta banda o tarifa' : 'Horas × tarifa',
  });
  return el(
    'tr',
    {},
    ...[person.name, hours(person.hours), person.band, person.band_month, personRate, cost].map(
      (value) => el('td', { text: text(value) }),
    ),
    el('td', {}, state),
  );
}

/** @param {any} group */
function groupTable(group) {
  const titles = ['Persona', 'Horas', 'Banda', 'Mes de banda', 'Tarifa interna de banda (USD/h)', 'Costo', 'Estado'];
  const head = el('tr', {}, ...titles.map((title) => el('th', { text: title })));
  const people = group.people || [];
  return [
    el('h4', { text: text(group.label) }),
    el('div', { style: { overflow: 'auto' } }, el('table', {}, head, ...people.map(personRow))),
    ...(people.length ? [] : [el('p', { text: 'Sin registros disponibles para este ID y periodo.' })]),
  ];
}

/**
 * Pide el desglose la primera vez que se abre cada detalle.
 * @param {HTMLElement} root
 * @param {() => Record<string, string>} period Filtros de periodo vigentes.
 */
export function bindPeople(root, period) {
  for (const details of /** @type {NodeListOf<HTMLDetailsElement>} */ (root.querySelectorAll('.opportunity-people'))) {
    let loaded = false;
    let busy = false;
    details.addEventListener('toggle', async () => {
      if (!details.open || loaded || busy) return;
      busy = true;
      const content = /** @type {HTMLElement} */ (details.querySelector('.opportunity-people-content'));
      content.textContent = 'Consultando personas y tarifas…';
      try {
        const { data } = await apiGet('costs/project/', {
          ...period(),
          id: details.dataset.project,
          nombre: details.dataset.account,
        });
        const sprints = data.sprints || [];
        const groups = sprints.some((/** @type {any} */ g) => /^(S[0-9]|CR)/i.test(g.label))
          ? sprints
          : [{ label: 'Personas', people: data.people || [] }];
        content.replaceChildren(
          el('p', { text: `Clockify: ${data.id} · ${data.scope_start || ''} a ${data.scope_end || ''}` }),
          ...groups.flatMap(groupTable),
        );
        loaded = true;
      } catch (error) {
        const message = error instanceof Error ? error.message : 'No se pudo consultar el detalle';
        content.textContent = `${message} · Cierra y abre para reintentar.`;
      } finally {
        busy = false;
      }
    });
  }
}
