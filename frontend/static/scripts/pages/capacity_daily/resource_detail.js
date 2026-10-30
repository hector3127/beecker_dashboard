// @ts-check
import { el } from '#app/lib/dom.js';
import { date, fmt, resourceDetail } from './model.js';

/** @param {any} data @param {string} name @param {() => void} close */
export function renderResourceDetail(data, name, close) {
  const model = resourceDetail(data, name);
  const heading = el('h3', { id: 'ci-person-heading', tabindex: '-1', text: name });
  const rows = model.rows.filter((/** @type {any} */ r) => r.idProyecto);
  const table = el('table', { class: 'ci-table' },
    el('caption', { text: 'Horas diarias por proyecto · ' + name }),
    el('thead', {}, el('tr', {}, ...['Proyecto', 'Total registrado', ...model.days.map(date)]
      .map((text) => el('th', { scope: 'col', text })))),
    el('tbody', {}, ...(rows.length ? rows : [{ idProyecto: 'Sin registros en el mes', proyecto: '', total: 0, daily: {} }])
      .map((/** @type {any} */ r) => el('tr', {},
        el('th', { scope: 'row', text: [r.idProyecto, r.proyecto].filter(Boolean).join(' · ') }),
        el('td', { text: fmt(r.total) + ' h' }),
        ...model.days.map((/** @type {string} */ d) => el('td', { text: r.daily[d] ? fmt(r.daily[d]) + ' h' : '' }))))));
  return el('section', { class: 'ci-card ci-person-detail', 'aria-labelledby': 'ci-person-heading' },
    el('div', { class: 'ci-section-head' }, heading,
      el('button', { type: 'button', class: 'ci-btn', text: '← Regresar al listado', onclick: close })),
    el('p', { class: 'ci-muted', text: 'Todas las horas de Clockify de esta persona en el mes, incluidas las no facturables y las de fines de semana. Los filtros del listado no ocultan sus proyectos aquí.' }),
    el('div', { class: 'ci-matrix', role: 'region', tabindex: '0', 'aria-label': 'Horas diarias por proyecto' }, table));
}
