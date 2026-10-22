// @ts-check
// Facturabilidad global por mes: cifra del mes, distancia a la meta y barras
// que se pueden elegir. Elegir un mes no pide datos: usa los ya cargados.
import { billingBars, percentText } from '#app/lib/charts.js';
import { el, svg } from '#app/lib/dom.js';
import { icon } from '#app/ui/icons.js';

/**
 * @typedef {object} BillingMonth
 * @property {string} month
 * @property {string} label
 * @property {string} month_label
 * @property {number | null} global_percent
 * @property {number | null} fixed_percent
 * @property {number | null} variable_percent
 */

const number = (/** @type {number | null} */ value, digits = 2) =>
  value === null || !Number.isFinite(value)
    ? '—'
    : `${value.toLocaleString('es-MX', { maximumFractionDigits: digits })}%`;

/**
 * Lo que se muestra para un mes: cifras, diferencia con la meta y etiqueta.
 * @param {BillingMonth} month
 * @param {{target: number, latestMonth: string | null, monthClosed: boolean}} context
 */
export function describeMonth(month, { target, latestMonth, monthClosed }) {
  const percent = month.global_percent;
  const gap = percent === null ? null : Math.round((percent - target) * 100) / 100;
  const latest = month.month === latestMonth;
  return {
    value: number(percent),
    fixed: `AER ${number(month.fixed_percent, 0)}`,
    variable: `PRJ ${number(month.variable_percent, 0)}`,
    gap,
    gapText:
      gap === null
        ? 'Sin datos para comparar con la meta'
        : `${gap >= 0 ? '↑' : '↓'} ${Math.abs(gap).toLocaleString('es-MX', { maximumFractionDigits: 1 })} puntos ${gap >= 0 ? 'arriba' : 'abajo'} de la meta`,
    label: `${month.month_label} · ${latest ? (monthClosed ? 'último mes cerrado' : 'mes en curso') : 'mes seleccionado'}`,
  };
}

/**
 * @param {any} data Contrato de facturabilidad.
 * @returns {HTMLElement}
 */
export function createBillingChart(data) {
  const months = /** @type {BillingMonth[]} */ (data.months);
  const context = { target: data.target, latestMonth: data.month, monthClosed: data.month_closed };
  const start = months.at(-1);

  const value = el('div', { class: 'billing-value', 'aria-live': 'polite' });
  const gap = el('div', { class: 'billing-gap' });
  const fixed = el('span', { class: 'billing-chip', title: 'Trabajo fijo: horas AER ÷ capacidad' });
  const variable = el('span', {
    class: 'billing-chip',
    title: 'Trabajo variable: TYM, IXB, SaaS y RaaS ÷ capacidad que queda',
  });
  const label = el('div', { class: 'billing-label' });
  const groups = /** @type {Map<string, SVGElement>} */ (new Map());

  /** @param {BillingMonth} month */
  function select(month) {
    const view = describeMonth(month, context);
    value.textContent = view.value;
    fixed.textContent = view.fixed;
    variable.textContent = view.variable;
    gap.textContent = view.gapText;
    gap.classList.toggle('is-down', view.gap !== null && view.gap < 0);
    gap.classList.toggle('is-none', view.gap === null);
    label.textContent = view.label;
    for (const [key, group] of groups) {
      const selected = key === month.month;
      group.setAttribute('aria-pressed', String(selected));
      group.classList.toggle('is-selected', selected);
    }
  }

  const layout = billingBars(months.map((m) => m.global_percent));
  const bars = months.map((month, index) => {
    const bar = layout[index];
    const text = percentText(month.global_percent);
    const group = svg(
      'g',
      {
        class: 'billing-bar',
        role: 'button',
        tabindex: 0,
        'aria-pressed': 'false',
        'aria-label': `${month.month_label}: ${text}`,
      },
      svg('title', {}, `${month.label}: ${text} de facturabilidad global`),
      svg('rect', { class: 'billing-rect', x: bar.x, y: bar.y, width: bar.width, height: bar.height, rx: 5 }),
      svg('text', { class: 'billing-text', x: bar.center, y: bar.textY, 'text-anchor': 'middle' }, text),
      svg('text', { class: 'billing-month', x: bar.center, y: 120, 'text-anchor': 'middle' }, month.label),
      svg('rect', { x: bar.x, y: 0, width: bar.width, height: 126, fill: 'transparent' }),
    );
    groups.set(month.month, group);
    group.addEventListener('click', () => select(month));
    group.addEventListener('keydown', (event) => {
      const key = /** @type {KeyboardEvent} */ (event).key;
      if (key === 'Enter' || key === ' ') {
        event.preventDefault();
        select(month);
      }
    });
    return group;
  });

  if (start) select(start);
  else {
    value.textContent = '—';
    gap.textContent = 'Sin datos para comparar con la meta';
    gap.classList.add('is-none');
    fixed.textContent = 'AER —';
    variable.textContent = 'PRJ —';
  }

  return el(
    'div',
    { class: 'billing' },
    el(
      'div',
      { class: 'billing-main' },
      el('div', { class: 'billing-title' }, el('span', { class: 'ops-icon violet' }, icon('chart')), 'Facturabilidad'),
      value,
      gap,
      el('div', { class: 'ops-muted', text: `Meta: ${Math.round(data.target)}% de la capacidad` }),
      el('div', { class: 'billing-chips' }, fixed, variable),
      label,
    ),
    el(
      'div',
      { class: 'billing-chart' },
      el('div', { class: 'billing-chart-title', text: 'Facturabilidad global por mes' }),
      bars.length
        ? svg(
            'svg',
            {
              viewBox: '0 0 520 126',
              width: '100%',
              class: 'billing-svg',
              role: 'group',
              'aria-label': 'Selecciona un mes para ver su facturabilidad',
            },
            ...bars,
          )
        : el('div', { class: 'ops-muted', text: 'Sin meses que mostrar.' }),
      data.errors.length
        ? el('div', { class: 'billing-errors', text: `Sin datos completos: ${data.errors.join('; ')}` })
        : '',
    ),
  );
}
