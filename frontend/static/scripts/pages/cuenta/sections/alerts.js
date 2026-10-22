// @ts-check
// Alertas de la cuenta y lista de oportunidades abiertas.
import { el, moreButton } from '#app/lib/dom.js';
import { alerts } from '#app/lib/account-metrics.js';

/**
 * @param {HTMLElement} container
 * @param {import('#app/lib/account-metrics.js').AccountProject[]} projects
 */
export function renderAlerts(container, projects) {
  const found = alerts(projects);
  const waiting = projects.some((p) => p.clockify_pending);
  container.append(
    el(
      'section',
      { class: 'card cuenta-panel', id: 'cuenta-alerts' },
      el('h2', { text: 'Alertas de cuenta' }),
      ...(found.length
        ? found.map(({ project, reason }) => el('div', { class: 'alert-card' }, el('b', { text: `${project.id} · ${project.name || ''}` }), el('br'), reason))
        : [el('p', { class: 'note', text: waiting ? 'Consultando consumos para revisar alertas...' : 'Sin alertas registradas' })]),
    ),
  );
}

/**
 * @param {HTMLElement} container
 * @param {any[]} opportunities
 * @param {() => void} onMore
 */
export function renderOpportunities(container, opportunities, onMore) {
  container.append(
    el(
      'section',
      { class: 'card cuenta-panel', id: 'cuenta-opportunities' },
      el('h2', {}, 'Oportunidades de la cuenta ', moreButton(onMore)),
      ...(opportunities.length
        ? opportunities.map((o) => el('div', { class: 'opportunity-row' }, el('span', { text: o.name }), el('span', { class: 'badge', text: o.stage })))
        : [el('p', { class: 'note', text: 'Sin oportunidades abiertas.' })]),
    ),
  );
}
