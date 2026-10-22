// @ts-check
// Tarjetas EVA: 1 (IXB y RaaS), 3 (AER y T&M) y 4 (servicios de ROC).
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { icon } from '#app/ui/icons.js';

const NO_VALUE = '—';
const RESTRICTED = 'Cifras del equipo completo: no disponibles con tu acceso.';

/** @param {string} label @param {string | number} value */
const stat = (label, value) => el('div', {}, el('div', { class: 'eva-label', text: label }), el('div', { class: 'eva-value', text: value }));
/** @param {string} href @param {string} text */
const more = (href, text) => el('a', { class: 'eva-more', href }, `${text} →`);

/**
 * @param {object} options
 * @param {string} options.title
 * @param {string} options.subtitle
 * @param {string} options.href
 * @param {string} options.ariaLabel
 * @param {string} options.daysLabel
 * @param {string} options.moreText
 * @param {any} options.card Contrato de la tarjeta, o null si el alcance no la permite.
 */
function timeCostCard({ title, subtitle, href, ariaLabel, daysLabel, moreText, card }) {
  const head = el(
    'div',
    { class: 'eva-head' },
    el('span', { class: 'eva-icon' }, icon('people', 26)),
    title,
    el('small', { text: subtitle }),
    el('a', { class: 'eva-go', href, 'aria-label': ariaLabel }, icon('arrow', 20)),
  );
  if (card === null) return el('div', { class: 'eva-card' }, head, el('p', { class: 'ops-muted', text: RESTRICTED }));
  const shown = card.available;
  return el(
    'div',
    { class: 'eva-card' },
    head,
    el(
      'div',
      { class: 'eva-stats' },
      stat('Proyectos (TP)', shown ? card.total_projects : NO_VALUE),
      stat(daysLabel, shown && card.time_days !== null ? `${formatNumber(card.time_days, 1)} d` : NO_VALUE),
      stat('Avance en horas', shown && card.cost_percent !== null ? `${formatNumber(card.cost_percent, 0)}%` : NO_VALUE),
    ),
    more(href, moreText),
  );
}

/**
 * @param {HTMLElement} root
 * @param {any} view Contrato de Operativa ya combinado.
 * @param {{eva1: string, eva3: string, eva4: string}} urls
 */
export function renderEva(root, view, urls) {
  const { eva1, eva3, eva4 } = view.eva;
  root.replaceChildren(
    timeCostCard({
      title: 'EVA 1',
      subtitle: 'IXB y RaaS',
      href: urls.eva1,
      ariaLabel: 'Ver detalle de EVA 1',
      daysLabel: 'Desviación (días)',
      moreText: 'Ver proyectos',
      card: eva1,
    }),
    timeCostCard({
      title: 'EVA 3',
      subtitle: 'AER y T&M',
      href: urls.eva3,
      ariaLabel: 'Ver detalle de EVA 3',
      daysLabel: 'Días para renovar',
      moreText: 'Ver por Delivery Manager',
      card: eva3,
    }),
    el(
      'div',
      { class: 'eva-card', id: 'ops-eva4-card' },
      el(
        'div',
        { class: 'eva-head' },
        el('span', { class: 'eva-title' }, 'EVA 4', el('small', { text: 'Servicios de ROC' })),
        el('a', { class: 'eva-go', href: urls.eva4, 'aria-label': 'Ver detalle de EVA-04 Report' }, icon('arrow', 20)),
      ),
      el(
        'div',
        { class: 'eva-stats' },
        stat('Activos', eva4.available ? eva4.active : NO_VALUE),
        stat('Suspendidos', eva4.available ? eva4.suspended : NO_VALUE),
        stat('Por renovar', eva4.available ? eva4.renewal_count : NO_VALUE),
      ),
      more(urls.eva4, 'Ver clientes, renovaciones y procesos'),
    ),
  );
}
