// @ts-check
import { el } from '#app/lib/dom.js';
import { resourceDetail, date, fmt } from './model.js';

/** @param {any} data @param {string} name @param {() => void} close */
export function renderResourceDetail(data, name, close) {
  const model = resourceDetail(data, name);
  const heading = el('h3', { id: 'ci-person-heading', tabindex: '-1', text: name });
  const table = el('table', { class: 'ci-table' },
    el('caption', { text: 'Horas diarias por proyecto · ' + name }),
    el('thead', {}, el('tr', {}, ...['Proyecto / concepto', 'Total registrado', ...model.days.map(date)]
      .map(text => el('th', { scope: 'col', text })))),
    el('tbody', {}, ...model.rows.map((/** @type {any} */ r) => el('tr', {},
      el('th', { scope: 'row', text: [r.idProyecto, r.proyecto, r.concepto].filter(Boolean).join(' · ') }),
      el('td', { text: fmt(r.total) + ' h' }),
      ...r.values.map((/** @type {number|null} */ value) => el('td', { text: value == null ? 'Pendiente' : fmt(value) + ' h' }))))));
  return el('section', { class: 'ci-card ci-person-detail', 'aria-labelledby': 'ci-person-heading' },
    el('div', { class: 'ci-section-head' }, heading,
      el('button', { type: 'button', class: 'ci-btn', text: '← Regresar al listado', onclick: close })),
    el('p', { class: 'ci-muted', text: 'Desglose de todas las asignaciones de esta persona en el mes seleccionado. Los filtros del listado no ocultan sus proyectos en este detalle. Desplaza la tabla horizontalmente para consultar cada día.' }),
    ...(model.pending ? [el('p', { class: 'ci-alert', text: 'Hay consultas o asignaciones pendientes. Las horas disponibles son parciales; pendiente no equivale a cero.' })] : []),
    el('div', { class: 'ci-matrix', role: 'region', tabindex: '0', 'aria-label': 'Horas diarias por proyecto' }, table));
}
