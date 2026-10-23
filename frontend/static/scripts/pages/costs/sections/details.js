// @ts-check
// Personas, bandas y tarifas de un proyecto, o su consumo por sprint y CR.
import { el } from '#app/lib/dom.js';
import { fmt, money, moneyRate } from './format.js';

const SPRINT = /^(?:S[0-9]|CR)/i;
const SPRINT_ID = /[_\s|-](?:S\d+|CR\d*)$/i;

/** @param {any} person @param {boolean} [future] */
function personRow(person, future = false) {
  return el(
    'tr',
    {},
    el('td', { text: person.name }),
    el('td', { text: future && person.future ? '—' : fmt(person.hours) }),
    el('td', { text: person.band || 'Sin banda' }),
    el('td', { text: person.band_month || 'Sin dato' }),
    el('td', { text: moneyRate(person.rate) }),
    el('td', { text: money(person.cost) }),
    el('td', { text: person.missing ? 'Incompleto' : 'Horas × tarifa' }),
  );
}

const PEOPLE_HEAD = ['Persona', 'Horas', 'Banda', 'Mes de banda', 'Tarifa/h', 'Costo', 'Estado'];
/** @param {any[]} rows */
const peopleTable = (rows) =>
  el('table', { class: 'people-table' }, el('thead', {}, el('tr', {}, ...PEOPLE_HEAD.map((text) => el('th', { text })))), el('tbody', {}, ...rows));

/** @param {any} group */
function sprintRows(group) {
  const people = group.people || [];
  return [
    el(
      'tr',
      {},
      el('td', { text: group.project_id }),
      el('td', { text: group.label }),
      el('td', { text: fmt(group.hours) }),
      el('td', { text: money(group.cost) }),
      el('td', { text: group.complete ? 'Calculado' : 'Costo parcial' }),
    ),
    el(
      'tr',
      { class: 'sprint-person-row' },
      el(
        'td',
        { colspan: 5 },
        el('details', { class: 'sprint-people' }, el('summary', { text: `Personas y esfuerzo (${people.length})` }), peopleTable(people.map((/** @type {any} */ p) => personRow(p)))),
      ),
    ),
  ];
}

/**
 * Contenido del desglose de un proyecto.
 * @param {any} data
 * @returns {Node[]}
 */
export function renderDetail(data) {
  const out = [el('p', { text: `Clockify: ${data.clockify_id || data.id} · Rango: ${data.scope_start || ''} a ${data.scope_end || ''}` })];
  const sprints = (data.sprints || []).filter((/** @type {any} */ g) => SPRINT.test(g.label));
  const bySprint = !SPRINT_ID.test(String(data.id || '')) && sprints.length > 0;
  if (bySprint) {
    out.push(
      el('h4', { text: `Consumo por sprint / CR / tareas (${sprints.length} sprints / CR)` }),
      el('p', { text: 'El revenue corresponde al proyecto completo; no se suma ni se reparte entre los sprints.' }),
      el(
        'table',
        { class: 'people-table sprint-table' },
        el('thead', {}, el('tr', {}, ...['Proyecto incluido', 'Sprint / CR / tareas', 'Horas', 'Costo', 'Estado'].map((text) => el('th', { text })))),
        el('tbody', {}, ...data.sprints.flatMap(sprintRows)),
      ),
    );
    if (!data.task_details_complete) out.push(el('p', { text: 'Hay tareas sin identificar. Sus horas y costos están incluidos en el total.' }));
  } else {
    out.push(el('h4', { text: `Personas (${data.people.length})` }), peopleTable(data.people.map((/** @type {any} */ p) => personRow(p, true))));
  }
  return out;
}
