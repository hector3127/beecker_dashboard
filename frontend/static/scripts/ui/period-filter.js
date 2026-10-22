// @ts-check
// Selector de periodo por mes, trimestre o año. Los enlaces ya vienen armados
// por el servidor (conservan los otros filtros de la pagina); este componente
// solo los reparte en pestanas.
import { el } from '#app/lib/dom.js';

/**
 * @typedef {{label: string, href: string, active: boolean, disabled: boolean}} PickerLink
 * @typedef {{year: number, active: boolean, months: PickerLink[], quarters: PickerLink[]}} PickerYear
 * @typedef {{label: string, kind: string, kind_label: string, years: PickerLink[], by_year: PickerYear[]}} Picker
 */

const KINDS = /** @type {const} */ ([
  ['mes', 'Mes'],
  ['trimestre', 'Trimestre'],
  ['anio', 'Año'],
]);

/** @param {PickerLink} link */
const option = (link) =>
  link.disabled ? el('span', { text: link.label }) : el('a', { href: link.href, class: link.active ? 'on' : '', 'aria-current': link.active ? 'true' : false, text: link.label });

/**
 * @param {HTMLElement} container
 * @param {Picker} picker
 */
export function mountPeriodFilter(container, picker) {
  let kind = picker.kind;
  let year = picker.by_year.find((y) => y.active)?.year ?? picker.by_year.at(-1)?.year;
  const kinds = el('ul', { class: 'pfp' });
  const body = el('div', { class: 'pfc' });

  function draw() {
    kinds.replaceChildren(...KINDS.map(([key, text]) => el('li', {}, el('button', { type: 'button', class: key === kind ? 'on' : '', text, onclick: () => ((kind = key), draw()) }))));
    /** @param {'months' | 'quarters'} field */
    const byYear = (field) => [
      el('div', { class: 'pfy' }, ...picker.by_year.map((y) => el('button', { type: 'button', class: y.year === year ? 'on' : '', text: String(y.year), onclick: () => ((year = y.year), draw()) }))),
      el('div', { class: 'pfr' }, ...(picker.by_year.find((y) => y.year === year)?.[field] || []).map(option)),
    ];
    body.replaceChildren(...(kind === 'mes' ? byYear('months') : kind === 'trimestre' ? byYear('quarters') : [el('div', { class: 'pfr' }, ...picker.years.map(option))]));
  }

  const details = /** @type {HTMLDetailsElement} */ (
    el('details', { class: 'pf', id: 'period-filter' }, el('summary', { 'aria-label': 'Cambiar periodo' }, el('span', { text: picker.label }), el('small', { text: picker.kind_label })), el('div', { class: 'pfm' }, kinds, body))
  );
  details.addEventListener('toggle', () => {
    if (details.open) {
      kind = picker.kind;
      year = picker.by_year.find((y) => y.active)?.year ?? year;
      draw();
    }
  });
  document.addEventListener('click', (event) => details.open && !details.contains(/** @type {Node} */ (event.target)) && (details.open = false));
  draw();
  container.replaceChildren(details);
}
