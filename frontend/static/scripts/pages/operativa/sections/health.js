// @ts-check
// Salud del portafolio: dona y tabla con el mismo desglose.
import { DONUT, donutArcs } from '#app/lib/charts.js';
import { el, svg } from '#app/lib/dom.js';

const NO_VALUE = '—';

/**
 * @param {HTMLElement} root
 * @param {any} view Contrato de Operativa ya combinado.
 */
export function renderHealth(root, view) {
  const { summary, health_states: states } = view;
  const hidden = view.loading || view.consumption_pending || view.portfolio_unavailable;
  const arcs = donutArcs(states.map((/** @type {{count: number}} */ s) => s.count));
  const circles = hidden
    ? []
    : states.flatMap((/** @type {{state: string, count: number}} */ s, /** @type {number} */ i) =>
        s.count
          ? [
              svg('circle', {
                class: `donut-arc ${s.state}`,
                cx: 88,
                cy: 88,
                r: DONUT.radius,
                'stroke-dasharray': `${arcs[i].dash.toFixed(1)} ${arcs[i].gap.toFixed(1)}`,
                'stroke-dashoffset': arcs[i].offset.toFixed(1),
              }),
            ]
          : [],
      );
  const center = hidden || view.loading || !summary.in_progress ? NO_VALUE : `${summary.on_time_percent}%`;
  const count = (/** @type {number | string} */ value) => (hidden ? NO_VALUE : value);

  root.replaceChildren(
    el(
      'header',
      { class: 'ops-health-header' },
      el('h2', { id: 'ops-health-title', text: 'Salud del portafolio' }),
      el('p', { text: `${count(summary.in_progress)} proyectos en ejecución` }),
    ),
    el(
      'div',
      { class: 'ops-health-layout' },
      el(
        'figure',
        { class: 'ops-health-figure' },
        svg(
          'svg',
          {
            width: 240,
            height: 240,
            viewBox: '0 0 176 176',
            role: 'img',
            'aria-label': 'Distribución de salud del portafolio; desglose en la tabla',
          },
          svg('g', { fill: 'none', 'stroke-width': 22, transform: 'rotate(-90 88 88)' }, ...circles),
          svg('text', { class: 'donut-value', x: 88, y: 92, 'text-anchor': 'middle' }, center),
          svg('text', { class: 'donut-caption', x: 88, y: 116.6, 'text-anchor': 'middle' }, 'Salud general'),
        ),
        el('figcaption', { text: 'Proyectos en tiempo' }),
      ),
      el(
        'div',
        { class: 'ops-health-breakdown' },
        el(
          'table',
          { class: 'ops-health-table' },
          el('caption', { text: 'Distribución de proyectos por estado' }),
          el('thead', {}, el('tr', {}, ...['Estado', 'Proyectos', '% del total'].map((t) => el('th', { scope: 'col', text: t })))),
          el(
            'tbody',
            {},
            ...states.map((/** @type {any} */ s) =>
              el(
                'tr',
                {},
                el(
                  'th',
                  { scope: 'row' },
                  el('span', { class: 'ops-health-state' }, el('i', { class: `state-dot ${s.state}`, 'aria-hidden': 'true' }), s.label),
                ),
                el('td', { text: count(s.count) }),
                el('td', { text: hidden ? NO_VALUE : `${s.percent}%` }),
              ),
            ),
          ),
        ),
      ),
      el('section',{class:'ops-service-distribution','aria-label':'Distribución por servicio'},
        el('h3',{text:'Distribución por servicio'}),
        ...(!Array.isArray(view.service_distribution) || view.loading || view.portfolio_unavailable
          ? [el('p',{class:'ops-muted',text:'Distribución pendiente de preparar.'})]
          : view.service_distribution.length ? view.service_distribution.map((service,index)=>{
            const meter=el('progress',{max:100,value:service.percent,'aria-label':`${service.service}: ${service.percent}%`});
            return el('div',{class:`ops-service-row service-tone-${index%4}`},el('span',{text:service.service}),meter,el('b',{text:service.count}),el('small',{text:`${service.percent}%`}));
          }) : [el('p',{class:'ops-muted',text:'Sin proyectos en ejecución.'})])
      ),
    ),
    el(
      'details',
      { class: 'ops-health-help' },
      el('summary', { 'aria-label': 'Cómo se calcula la salud del portafolio', title: 'Cómo se calcula la salud del portafolio', text: '!' }),
      el('p', {
        class: 'ops-health-footnote',
        text: `Salud = proyectos en tiempo entre proyectos en ejecución (${count(summary.health.on_time)} de ${count(summary.in_progress)}). Los ${count(summary.paused)} suspendidos no se cuentan.`,
      }),
    ),
  );
}
