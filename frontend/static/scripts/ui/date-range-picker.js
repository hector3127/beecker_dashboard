// @ts-check
// Selector de rango Desde–Hasta con calendario doble.
// Trabaja sobre el HTML de la plantilla (details#executive-date-picker).
import { cells, date, iso } from '#app/lib/calendar.js';
import { el } from '#app/lib/dom.js';

const WEEKDAYS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do'];
const MAX_DAYS = 1096;

/** @param {HTMLDetailsElement} details @param {HTMLFormElement} form */
export function mountDateRangePicker(details, form) {
  const field = (/** @type {string} */ name) => /** @type {HTMLInputElement} */ (form.elements.namedItem(name));
  const byId = (/** @type {string} */ id) => /** @type {HTMLElement} */ (document.getElementById(id));
  const from = field('desde');
  const to = field('hasta');
  const preview = byId('picker-preview');
  const error = byId('picker-error');
  const view = /** @type {HTMLInputElement} */ (byId('picker-view'));
  const today = new Date();
  const applied = [form.dataset.start || iso(new Date(today.getFullYear(), 0, 1)), form.dataset.end || iso(new Date(today.getFullYear(), 11, 31))];
  let base = date(applied[0]);
  let choosingEnd = false;
  const format = (/** @type {string} */ s) => (s ? date(s).toLocaleDateString('es-MX', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—');

  function paint() {
    preview.textContent = from.value ? `${format(from.value)} - ${format(to.value)}` : 'Selecciona un rango';
    view.value = 'custom';
    ['picker-month-left', 'picker-month-right'].forEach((id, index) => {
      const target = byId(id);
      const month = new Date(base.getFullYear(), base.getMonth() + index, 1);
      const grid = el('div', { class: 'calendar-grid' }, ...WEEKDAYS.map((label) => el('span', { class: 'calendar-weekday', text: label })));
      for (const cell of cells(month.getFullYear(), month.getMonth())) {
        const selected = Boolean(from.value && to.value && cell.key >= from.value && cell.key <= to.value);
        const day = el('button', {
          type: 'button',
          class: 'calendar-day',
          text: cell.day,
          'data-date': cell.key,
          'aria-label': date(cell.key).toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
          'aria-pressed': String(selected || cell.key === from.value),
          tabindex: cell.outside ? -1 : 0,
        });
        day.classList.toggle('outside', cell.outside);
        day.classList.toggle('today', cell.key === iso(today));
        day.classList.toggle('in-range', selected);
        day.classList.toggle('boundary', cell.key === from.value || cell.key === to.value);
        grid.append(day);
      }
      target.replaceChildren(el('h4', { text: month.toLocaleDateString('es-MX', { month: 'long', year: 'numeric' }) }), grid);
    });
  }

  /** @param {string[]} values */
  function setRange(values) {
    [from.value, to.value] = values;
    base = date(from.value);
    choosingEnd = false;
    error.textContent = '';
    to.setCustomValidity('');
    paint();
  }
  function reset() {
    setRange(applied);
  }

  /** @param {number} delta */
  const shift = (delta) => {
    base = new Date(base.getFullYear(), base.getMonth() + delta, 1);
    paint();
  };
  /** @type {HTMLElement} */ (form.querySelector('.calendar-prev')).addEventListener('click', () => shift(-1));
  /** @type {HTMLElement} */ (form.querySelector('.calendar-next')).addEventListener('click', () => shift(1));
  /** @type {HTMLElement} */ (form.querySelector('.picker-calendars')).addEventListener('click', (event) => {
    const button = /** @type {HTMLElement | null} */ (/** @type {Element} */ (event.target).closest('[data-date]'));
    if (!button) return;
    const key = /** @type {string} */ (button.dataset.date);
    if (!choosingEnd) {
      from.value = key;
      to.value = '';
      choosingEnd = true;
    } else {
      const start = from.value;
      from.value = start < key ? start : key;
      to.value = start < key ? key : start;
      choosingEnd = false;
    }
    error.textContent = '';
    to.setCustomValidity('');
    paint();
    /** @type {HTMLElement | null} */ (form.querySelector(`[data-date="${key}"]`))?.focus();
  });
  for (const input of [from, to]) {
    input.addEventListener('input', () => {
      choosingEnd = false;
      to.setCustomValidity('');
      error.textContent = '';
      if (from.value) base = date(from.value);
      paint();
    });
  }
  byId('picker-clear').addEventListener('click', () => {
    from.value = to.value = '';
    choosingEnd = false;
    error.textContent = '';
    paint();
    from.focus();
  });
  const close = () => {
    reset();
    details.open = false;
    /** @type {HTMLElement} */ (details.querySelector('summary')).focus();
  };
  byId('picker-cancel').addEventListener('click', close);
  form.addEventListener('submit', (event) => {
    if (!from.value || !to.value || from.value > to.value) {
      event.preventDefault();
      error.textContent = 'Selecciona una fecha inicial y una fecha final posterior.';
      return;
    }
    if ((date(to.value).getTime() - date(from.value).getTime()) / 86400000 > MAX_DAYS) {
      event.preventDefault();
      error.textContent = 'El rango máximo es de tres años.';
    }
  });
  details.addEventListener('toggle', () => {
    if (details.open) reset();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && details.open) close();
  });
  document.addEventListener('click', (event) => {
    // paint() reemplaza el día pulsado; la ruta original conserva su pertenencia al selector.
    if (details.open && !event.composedPath().includes(details)) details.open = false;
  });
  reset();
}
