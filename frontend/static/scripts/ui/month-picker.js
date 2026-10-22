// @ts-check
// Selector de mes: flechas y listas de mes y ano, limitado a un rango.
// No pide datos: avisa el mes elegido con onChange y la pantalla decide.
import { el } from '#app/lib/dom.js';

const ICON =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">' +
  '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4M7 14h2m3 0h2M7 17h2"/></svg>';

/** "2026-10" -> numero de mes comparable. @param {string} value */
export function monthIndex(value) {
  const [year, month] = value.split('-').map(Number);
  return year * 12 + month - 1;
}

/** Numero de mes -> "2026-10". @param {number} index */
export const monthValue = (index) => `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}`;

/**
 * Mueve un mes dentro del rango; nunca sale de [min, max].
 * @param {string} value
 * @param {number} delta Meses a mover (puede ser negativo).
 * @param {string} min
 * @param {string} max
 */
export function shiftMonth(value, delta, min, max) {
  return monthValue(Math.min(monthIndex(max), Math.max(monthIndex(min), monthIndex(value) + delta)));
}

/**
 * @typedef {object} PickerConfig
 * @property {string} value Mes mostrado, AAAA-MM.
 * @property {string} min
 * @property {string} max
 * @property {number[]} years
 * @property {{num: number, name: string}[]} months
 */

/**
 * @param {PickerConfig} config
 * @param {{label: string, ariaLabel: string, onChange: (value: string) => void}} options
 */
export function createMonthPicker(config, { label, ariaLabel, onChange }) {
  const { min, max } = config;
  let current = config.value;
  const titleId = 'month-picker-title';
  const month = el(
    'select',
    { 'aria-label': 'Mes' },
    ...config.months.map((m) => el('option', { value: m.num, text: m.name })),
  );
  const year = el('select', { 'aria-label': 'Año' }, ...config.years.map((y) => el('option', { value: y, text: y })));
  const prev = el('button', { type: 'button', class: 'month-step', 'aria-label': 'Mes anterior', text: '‹' });
  const next = el('button', { type: 'button', class: 'month-step', 'aria-label': 'Mes siguiente', text: '›' });
  const icon = el('span', { class: 'month-picker-icon', 'aria-hidden': 'true' });
  icon.innerHTML = ICON; // constante del modulo, sin datos del servidor
  const form = el(
    'form',
    { class: 'month-picker', 'aria-label': ariaLabel, onsubmit: (event) => event.preventDefault() },
    icon,
    el(
      'div',
      { class: 'month-picker-field' },
      el('span', { class: 'month-picker-title', id: titleId, text: label }),
      el('div', { class: 'month-picker-controls', role: 'group', 'aria-labelledby': titleId }, prev, month, year, next),
    ),
  );

  function sync() {
    const index = monthIndex(current);
    /** @type {HTMLSelectElement} */ (month).value = String((index % 12) + 1);
    /** @type {HTMLSelectElement} */ (year).value = String(Math.floor(index / 12));
    /** @type {HTMLButtonElement} */ (prev).disabled = index <= monthIndex(min);
    /** @type {HTMLButtonElement} */ (next).disabled = index >= monthIndex(max);
    for (const option of /** @type {HTMLSelectElement} */ (month).options) {
      const candidate = Number(/** @type {HTMLSelectElement} */ (year).value) * 12 + Number(option.value) - 1;
      option.disabled = candidate < monthIndex(min) || candidate > monthIndex(max);
    }
  }

  /** @param {number} index */
  function go(index) {
    const value = shiftMonth(monthValue(index), 0, min, max);
    if (value === current) return sync(); // restaura las listas si pidieron un mes fuera de rango
    current = value;
    sync();
    onChange(value);
  }

  const picked = () =>
    Number(/** @type {HTMLSelectElement} */ (year).value) * 12 + Number(/** @type {HTMLSelectElement} */ (month).value) - 1;
  prev.addEventListener('click', () => go(monthIndex(current) - 1));
  next.addEventListener('click', () => go(monthIndex(current) + 1));
  month.addEventListener('change', () => go(picked()));
  year.addEventListener('change', () => go(picked()));
  sync();

  return {
    element: form,
    /** Cambia el mes mostrado sin avisar (por ejemplo al regresar en el historial). @param {string} value */
    setValue(value) {
      current = shiftMonth(value, 0, min, max);
      sync();
    },
    /** Deshabilita el selector mientras se consulta. @param {boolean} busy */
    setBusy(busy) {
      form.classList.toggle('is-loading', busy);
      if (busy) form.setAttribute('aria-busy', 'true');
      else form.removeAttribute('aria-busy');
    },
  };
}
