// @ts-check
// Indicadores de la cuenta y el avance de consumo presupuestal.
import { el, svg } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { serviceHours } from '#app/lib/account-summary.js';

/** Horas con un decimal y la unidad. @param {unknown} value */
export const hours = (value) => `${Number(value || 0).toLocaleString('es-MX', { maximumFractionDigits: 1 })} h`;

/**
 * Icono de trazo de 24x24.
 * @param {string} className
 * @param {[string, Record<string, string | number>][]} shapes
 */
function icon(className, shapes) {
  return el(
    'span',
    { class: className },
    svg('svg', { viewBox: '0 0 24 24' }, ...shapes.map(([tag, attrs]) => svg(tag, attrs))),
  );
}

/**
 * @param {string} iconClass
 * @param {[string, Record<string, string | number>][]} shapes
 * @param {string} label
 * @param {string} value
 * @param {Node | string} note
 * @param {Record<string, any>} [props]
 */
function card(iconClass, shapes, label, value, note, props = {}) {
  return el(
    'div',
    { class: 'account-card', ...props },
    icon(`account-icon${iconClass}`, shapes),
    el('small', { text: label }),
    el('strong', { text: value }),
    el('p', { class: 'account-muted' }, note),
  );
}

/**
 * @param {any} data La seccion de la API.
 * @param {{progress: number | null, total: number}} summary
 * @param {any[]} projects
 * @param {{roc: () => void}} actions
 */
export function renderKpis(data, summary, projects, actions) {
  const consumption = el(
    'div',
    { class: 'account-card consumption-kpi' },
    icon('account-icon green', [['ellipse', { cx: 12, cy: 5, rx: 7, ry: 3 }], ['path', { d: 'M5 5v14c0 4 14 4 14 0V5M5 10c0 4 14 4 14 0M5 15c0 4 14 4 14 0' }]]),
    el('small', { text: 'Consumo presupuestal' }),
    el('strong', { id: 'account-total-consumption', text: '—' }),
    el('div', { class: 'consumption-track' }, el('i', { id: 'account-consumption-bar' })),
    el('p', { class: 'account-muted', id: 'account-total-variance' }),
  );
  return el(
    'div',
    { class: 'account-kpis' },
    card(' green', [['circle', { cx: 12, cy: 12, r: 9 }], ['path', { d: 'm8 12 3 3 5-6' }]], 'Satisfacción del cliente', data.nps !== null && data.nps !== undefined ? `${data.nps} NPS` : '—', `${data.nps_sample} proyectos con NPS`),
    card('', [['circle', { cx: 12, cy: 12, r: 9 }], ['path', { d: 'M12 6v6l4 2' }]], 'Avance promedio de proyectos', summary.progress !== null ? `${formatNumber(summary.progress, 1)}%` : '—', 'Consumo / presupuesto · corte disponible'),
    card(' green', [['rect', { x: 4, y: 5, width: 16, height: 15, rx: 2 }], ['path', { d: 'M8 3v4M16 3v4M4 10h16M8 14h2M14 14h2' }]], 'Total de proyectos', String(summary.total), 'Histórico y MPB de la cuenta'),
    card(
      '',
      [['path', { d: 'm9 3-1 3-3 1v4l-2 1 2 2v4l3 1 1 3h6l1-3 3-1v-4l2-2-2-1V7l-3-1-1-3z' }], ['circle', { cx: 12, cy: 12, r: 3 }]],
      'Procesos activos en ROC',
      String(data.roc_active),
      el('span', {}, 'Procesos de esta cuenta ', el('button', { class: 'account-more', id: 'roc-more', text: 'Ver más ↗', onclick: actions.roc })),
    ),
    consumption,
  );
}

/** Consumo total y por servicio con las horas que ya llegaron. @param {any[]} projects */
export function updateConsumption(projects) {
  const burn = projects.reduce((n, p) => n + Number(p.burn || 0), 0);
  const budget = projects.reduce((n, p) => n + Number(p.budget || 0), 0);
  const ratio = budget > 0 ? (burn / budget) * 100 : null;
  const total = /** @type {HTMLElement} */ (document.getElementById('account-total-consumption'));
  const bar = /** @type {HTMLElement} */ (document.getElementById('account-consumption-bar'));
  total.textContent = ratio === null ? '—' : `${Math.round(ratio)}%`;
  total.style.color = ratio !== null && ratio > 100 ? '#e93764' : '#008c70';
  bar.style.width = `${Math.min(100, Math.max(0, ratio || 0))}%`;
  bar.style.background = ratio !== null && ratio > 100 ? '#ef4e73' : 'linear-gradient(90deg,#42d6ad,#12aa73)';
  const variance = /** @type {HTMLElement} */ (document.getElementById('account-total-variance'));
  variance.textContent = `${hours(burn)} de ${hours(budget)}`;

  const groups = serviceHours(projects);
  const maximum = Math.max(1, ...[...groups.values()].flatMap((g) => [g.budget, g.burn]));
  const container = /** @type {HTMLElement} */ (document.querySelector('.account-service-chart'));
  container.replaceChildren(
    ...[...groups.entries()].map(([name, g]) => {
      const bars = el('div', { class: 'account-service-bars' });
      for (const [key, color] of /** @type {const} */ ([['budget', '#d2c3fb'], ['burn', '#7450ed']])) {
        const bar = el('i', { title: `${key}: ${hours(g[key])}` });
        bar.style.height = `${(g[key] / maximum) * 100}%`;
        bar.style.background = color;
        bars.append(bar);
      }
      const label = el('span', { text: `${name} · ${g.budget ? `${Math.round((g.burn / g.budget) * 100)}%` : 'NA'}` });
      label.style.color = g.budget && g.burn > g.budget ? '#e42e62' : '#009971';
      return el('div', { class: 'account-service-column' }, bars, label);
    }),
  );
}
