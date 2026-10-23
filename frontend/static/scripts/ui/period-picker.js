// @ts-check
// Selector de periodo con mes, trimestre y año. Los enlaces (con el periodo ya
// escrito en la URL) vienen de la API; aqui solo se elige que lista ver.
import { el, svg } from '#app/lib/dom.js';

const KINDS = [
  ['mes', 'Mes'],
  ['trimestre', 'Trimestre'],
  ['anio', 'Año'],
];

/** @param {any} link */
function chip(link) {
  if (link.disabled) return el('span', { text: link.label });
  return el('a', { class: link.active ? 'on' : null, href: link.href, text: link.label });
}

/**
 * @param {any} picker label, kind, kind_label, years y by_year de la API.
 * @param {string} [id]
 * @returns {HTMLDetailsElement}
 */
export function createPeriodPicker(picker, id = 'period-filter') {
  /** Botones de año y, debajo, la lista de cada año. @param {(item: any) => any[]} links */
  const byYear = (links) => [
    el('div', { class: 'pfy' }, ...picker.by_year.map((/** @type {any} */ item) => el('button', { type: 'button', 'data-y': item.year, class: item.active ? 'on' : null, text: item.year }))),
    ...picker.by_year.map((/** @type {any} */ item) => el('div', { class: 'pfr', 'data-y': item.year, hidden: !item.active }, el('div', {}, ...links(item).map(chip)))),
  ];

  const panes = [
    el('div', { class: 'pfk', 'data-k': 'mes', hidden: picker.kind !== 'mes' }, ...byYear((item) => item.months)),
    el('div', { class: 'pfk', 'data-k': 'trimestre', hidden: picker.kind !== 'trimestre' }, ...byYear((item) => item.quarters)),
    el('div', { class: 'pfk', 'data-k': 'anio', hidden: picker.kind !== 'anio' }, el('div', { class: 'pfr' }, el('div', {}, ...picker.years.map(chip)))),
  ];
  const icon = svg(
    'svg',
    { width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: '#4B25C9', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' },
    svg('rect', { x: 3, y: 5, width: 18, height: 16, rx: 2 }),
    svg('path', { d: 'M3 10h18M8 3v4M16 3v4' }),
  );
  const details = /** @type {HTMLDetailsElement} */ (
    el(
      'details',
      { class: 'pf', id },
      el('summary', { 'aria-label': 'Cambiar periodo' }, icon, el('span', { text: picker.label }), el('small', { text: picker.kind_label })),
      el(
        'div',
        { class: 'pfm' },
        el('ul', { class: 'pfp' }, ...KINDS.map(([kind, text]) => el('li', {}, el('button', { type: 'button', 'data-k': kind, class: picker.kind === kind ? 'on' : null, text })))),
        el('div', { class: 'pfc' }, ...panes),
      ),
    )
  );

  details.addEventListener('click', (event) => {
    const button = /** @type {HTMLElement} */ (event.target).closest('button');
    if (!button) return;
    if (button.dataset.k) {
      details.querySelectorAll('.pfp button').forEach((b) => b.classList.toggle('on', b === button));
      details.querySelectorAll('.pfk').forEach((pane) => {
        /** @type {HTMLElement} */ (pane).hidden = /** @type {HTMLElement} */ (pane).dataset.k !== button.dataset.k;
      });
    } else if (button.dataset.y) {
      details.querySelectorAll('.pfy button').forEach((b) => b.classList.toggle('on', /** @type {HTMLElement} */ (b).dataset.y === button.dataset.y));
      details.querySelectorAll('.pfk .pfr[data-y]').forEach((row) => {
        /** @type {HTMLElement} */ (row).hidden = /** @type {HTMLElement} */ (row).dataset.y !== button.dataset.y;
      });
    }
  });
  document.addEventListener('click', (event) => {
    if (details.open && !details.contains(/** @type {Node} */ (event.target))) details.removeAttribute('open');
  });
  return details;
}
