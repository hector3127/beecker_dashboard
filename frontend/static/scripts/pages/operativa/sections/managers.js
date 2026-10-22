// @ts-check
// Delivery Managers: una tarjeta por persona en un carrusel con desplazamiento.
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';

const NO_VALUE = '—';

/** Texto cuando no hay tarjetas que mostrar. @param {any} view */
function emptyText(view) {
  if (view.loading) return 'Calculando proyectos por Delivery Manager…';
  if (view.portfolio_unavailable) return 'No se pudieron consultar los proyectos. Vuelve a actualizar los datos.';
  if (view.filters.service || view.filters.client) return 'Ningún proyecto coincide con los filtros.';
  return 'Sin proyectos que mostrar todavía.';
}

/** @param {number} value @param {boolean} ready */
const hours = (value, ready) => (ready ? `${formatNumber(value, 1)} h` : NO_VALUE);
/** @param {string} label @param {string | number} value */
const row = (label, value) => el('div', { class: 'm2' }, el('span', { text: label }), el('b', { text: value }));

/**
 * @param {any} manager
 * @param {any} view
 * @param {{managerUrl: string}} urls
 */
function managerCard(manager, view, urls) {
  const { health, shares, investment } = manager;
  const pending = view.consumption_pending;
  const href = `${urls.managerUrl.replace('slug-placeholder', manager.slug)}?nombre=${encodeURIComponent(manager.name)}`;
  const segment = (/** @type {string} */ state, /** @type {number} */ share) => {
    const bar = el('i', { class: `dm-segment ${state}` });
    bar.style.width = `${share.toFixed(1)}%`;
    return bar;
  };
  const bar = el('div', { class: 'dm-bar' });
  if (health.on_time) bar.append(segment('on_time', shares.on_time));
  if (health.at_risk) bar.append(segment('at_risk', shares.at_risk));
  if (health.critical) bar.append(segment('critical', shares.critical));
  return el(
    'div',
    { class: 'dm-card' },
    el(
      'div',
      { class: 'dm-card-head' },
      el('span', { class: 'ops-icon brand', text: manager.initials }),
      el('div', {}, el('b', {}, el('a', { href, text: manager.name })), el('div', { class: 'dm-role', text: 'Delivery Manager' })),
    ),
    pending
      ? el('p', { class: 'ops-muted dm-pending', text: 'Proyectos disponibles. Calculando consumo y salud…' })
      : el(
          'div',
          {},
          bar,
          el(
            'div',
            { class: 'dm-counts' },
            el('span', { text: `${health.on_time} en tiempo` }),
            el('span', { text: `${health.at_risk} en riesgo` }),
            el('span', { text: `${health.critical} ${health.critical === 1 ? 'crítico' : 'críticos'}` }),
          ),
        ),
    row('Proyectos', manager.in_progress + manager.paused),
    row('Suspendidos', manager.paused),
    row('En tiempo', pending ? NO_VALUE : health.on_time),
    row('En ejecución', manager.in_progress),
    el(
      'div',
      { class: 'dm-investment' },
      row('Inversión comercial', hours(investment.commercial, investment.ready)),
      row('Inversión operativa', hours(investment.operational, investment.ready)),
    ),
  );
}

/**
 * Reemplaza el contenido de la seccion conservando su encabezado.
 * @param {HTMLElement} root La seccion #ops-managers.
 * @param {any} view Contrato de Operativa ya combinado.
 * @param {{managerUrl: string, investmentUrl: string}} urls
 */
export function renderManagers(root, view, urls) {
  const oldTrack = root.querySelector('.dm-track');
  const scroll = oldTrack ? oldTrack.scrollLeft : 0;
  root.querySelector('.dm-carousel, .vacio')?.remove();
  if (!view.managers.length) {
    root.append(el('div', { class: 'vacio', text: emptyText(view) }));
    return;
  }
  const track = el('div', { class: 'dm-track', tabindex: 0, 'aria-label': 'Tarjetas de Delivery Managers; desplaza para ver todos' });
  track.append(...view.managers.map((/** @type {any} */ m) => managerCard(m, view, urls)));
  const step = (/** @type {number} */ direction) => () => {
    const first = track.firstElementChild;
    if (!first) return;
    track.scrollBy({
      left: direction * (first.getBoundingClientRect().width + 14),
      behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    });
  };
  root.append(
    el(
      'section',
      { class: 'dm-carousel', 'aria-label': 'Delivery Managers' },
      el(
        'div',
        { class: 'dm-controls' },
        el('a', { class: 'dm-investment-link', href: urls.investmentUrl, text: 'Inversión mensual del equipo' }),
        el(
          'div',
          {},
          el('button', { type: 'button', 'aria-label': 'Ver Delivery Managers anteriores', onclick: step(-1), text: '←' }),
          el('button', { type: 'button', 'aria-label': 'Ver siguientes Delivery Managers', onclick: step(1), text: '→' }),
        ),
      ),
      track,
    ),
  );
  track.scrollLeft = scroll;
}
