// @ts-check
// Cabecera del Delivery Manager y sus seis indicadores.
import { el, svg } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';

/** @typedef {[string, Record<string, string | number>]} Shape */

/** @type {Record<string, Shape[]>} */
const SHAPES = {
  folder: [['path', { d: 'M3 7h6l2 2h10v11H3z' }]],
  clock: [['circle', { cx: 12, cy: 12, r: 9 }], ['path', { d: 'M12 6v6h4' }]],
  warning: [['path', { d: 'M12 3 2 21h20zM12 9v5M12 17v1' }]],
  bars: [['path', { d: 'M5 20V13M12 20V7M19 20V3' }]],
  commercial: [['path', { d: 'm3 10 4-5 5 2 5-2 4 5-3 9-6 2-6-2zM7 11l5 5 5-5' }]],
  database: [['ellipse', { cx: 12, cy: 5, rx: 8, ry: 3 }], ['path', { d: 'M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0' }]],
};

/** Icono de trazo; el mismo para los indicadores y los encabezados de seccion. @param {keyof typeof SHAPES} name */
export function icon(name) {
  return el(
    'span',
    { class: 'metric-icon' },
    svg(
      'svg',
      { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' },
      ...SHAPES[name].map(([tag, attrs]) => svg(tag, attrs)),
    ),
  );
}

const DASH = '—';
/** @param {number} n @param {string} one @param {string} many */
const plural = (n, one, many) => (n === 1 ? one : many);
/** @param {number} value */
const hoursText = (value) => `${formatNumber(value, 2)} h`;

/** @param {string} name @param {string} initials @param {string} subtitle */
export function renderHead(name, initials, subtitle) {
  return [
    el('div', { class: 'av', text: initials }),
    el('div', {}, el('h1', { text: name }), el('p', { class: 'sub', text: subtitle })),
  ];
}

/** @param {any} summary */
export function subtitle(summary) {
  const n = summary.total;
  return `Delivery Manager · ${n} proyecto${plural(n, '', 's')} asignado${plural(n, '', 's')}`;
}

/**
 * @param {keyof typeof SHAPES} name
 * @param {string} label
 * @param {string} value
 * @param {string} extra
 */
function card(name, label, value, extra) {
  return el(
    'div',
    { class: 'kc' },
    icon(name),
    el('div', {}, el('div', { class: 'kl', text: label }), el('div', { class: 'kv', text: value }), el('div', { class: 'ke', text: extra })),
  );
}

/** Los indicadores mientras llega la base. */
export function loadingCards() {
  const wait = (/** @type {keyof typeof SHAPES} */ name, /** @type {string} */ label) => card(name, label, DASH, 'Cargando…');
  return [
    wait('folder', 'Proyectos'),
    wait('clock', 'En tiempo'),
    wait('warning', 'Proyectos críticos'),
    wait('bars', 'Suspendidos'),
    wait('commercial', 'Inversión comercial'),
    wait('database', 'Inversión operativa'),
  ];
}

/** @param {any} data */
export function renderCards(data) {
  const { summary, investment } = data;
  const { health } = summary;
  /** @param {number | null} value */
  const spent = (value) => {
    if (investment.state === 'pending') return '…';
    return investment.state === 'ready' && value !== null ? hoursText(value) : DASH;
  };
  const note = 'Proyectos en curso, incluidos suspendidos';
  return [
    card('folder', 'Proyectos', String(summary.total), `${summary.in_progress} en ejecución y ${summary.paused} suspendido${plural(summary.paused, '', 's')}`),
    card('clock', 'En tiempo', String(health.on_time), `${health.at_risk} en riesgo y ${health.critical} crítico${plural(health.critical, '', 's')}`),
    card('warning', 'Proyectos críticos', String(health.critical), 'Proyectos activos en estado crítico'),
    card('bars', 'Suspendidos', String(summary.paused), 'Proyectos suspendidos del DM'),
    card('commercial', 'Inversión comercial', spent(investment.commercial), note),
    card('database', 'Inversión operativa', spent(investment.operational), note),
  ];
}
