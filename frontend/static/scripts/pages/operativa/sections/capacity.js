// @ts-check
// Capacidad del equipo: horas disponibles y como se reparten.
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { icon } from '#app/ui/icons.js';

const NO_VALUE = '—';
const RESTRICTED = 'Cifras del equipo completo: no disponibles con tu acceso.';

/** @param {string} label @param {number | null} value @param {number} [digits] */
const hoursStat = (label, value, digits = 2) => el('span', {}, `${label}: `, el('b', { text: `${formatNumber(value ?? 0, digits)} h` }));

/** Ancho del medidor: horas facturables entre la capacidad base, entre 0 y 100. */
export function meterPercent(billable, base) {
  return base ? Math.min(100, Math.max(0, Math.round((billable / base) * 100))) : 0;
}

/**
 * @param {HTMLElement} root
 * @param {any} capacity Contrato de capacidad, o null si el alcance no la permite.
 */
export function renderCapacity(root, capacity) {
  if (capacity === null) {
    root.replaceChildren(el('p', { class: 'ops-muted', text: RESTRICTED }));
    return;
  }
  const known = !capacity.error && capacity.available !== null && capacity.available !== undefined;
  const left = el(
    'div',
    {},
    el('div', { class: 'ops-heading' }, el('span', { class: 'ops-icon blue' }, icon('team')), 'Capacidad instalada'),
    el(
      'div',
      { class: 'ops-number' },
      known ? formatNumber(capacity.available, 0) : NO_VALUE,
      ' ',
      el('small', { text: capacity.loading ? 'Calculando…' : 'horas disponibles' }),
    ),
    el('div', {
      class: 'ops-muted',
      text: capacity.loading ? '' : `${capacity.month} · ${capacity.registered_people || 0} recursos con registros`,
    }),
  );
  let right;
  if (capacity.loading) {
    right = el('p', { class: 'ops-muted', text: 'Calculando capacidad y horas registradas…' });
  } else if (capacity.error) {
    right = el('p', { class: 'ops-muted', text: capacity.error });
  } else {
    const meter = el('div', { class: 'ops-meter', role: 'img', 'aria-label': 'Proporción de horas facturables respecto a capacidad base' }, el('i'));
    /** @type {HTMLElement} */ (meter.firstElementChild).style.width = `${meterPercent(capacity.billable, capacity.base)}%`;
    right = el(
      'div',
      {},
      meter,
      el('div', { class: 'ops-stats' }, hoursStat('Estimadas (Recursos)', capacity.estimated), hoursStat('Consumo actual (Clockify)', capacity.consumed)),
      el('p', { class: 'ops-muted', text: 'Estimaciones de las asignaciones de recursos con registros en el mes seleccionado.' }),
      el(
        'div',
        { class: 'ops-stats' },
        el('span', {}, el('i', { class: 'ops-dot' }), 'Horas facturables: ', el('b', { text: `${formatNumber(capacity.billable ?? 0)} h` })),
        el(
          'span',
          {},
          el('i', { class: 'ops-dot light' }),
          'Disponibles: ',
          el('b', { text: capacity.available !== null ? `${formatNumber(capacity.available)} h` : 'Pendiente' }),
        ),
      ),
      el('p', {
        class: 'ops-muted',
        text:
          `Capacidad base del mes: ${formatNumber(capacity.base ?? 0, 0)} h (${capacity.days} días × 8 h). ${capacity.over} personas sobre jornada.` +
          (capacity.pending ? ` ${capacity.pending} asignaciones pendientes; horas parciales.` : ''),
      }),
    );
  }
  root.replaceChildren(left, right);
}
