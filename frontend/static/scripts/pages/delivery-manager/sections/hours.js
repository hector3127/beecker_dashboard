// @ts-check
// Consumo de horas por mes: grafica de barras, detalle por proyecto y CSV.
import { el, svg } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { HOUR_KEYS, hoursScale, monthCsv } from '#app/lib/hours-report.js';
import { openDetail } from '#app/ui/detail-dialog.js';

const LABELS = ['Facturables', 'Inversión operativa', 'Inversión comercial'];
const hours = (/** @type {number | null | undefined} */ value) => `${formatNumber(Number(value || 0), 1)} h`;

/** @param {import('#app/lib/hours-report.js').HoursMonth} month */
function download(month) {
  const url = URL.createObjectURL(new Blob([monthCsv(month)], { type: 'text/csv;charset=utf-8' }));
  const link = el('a', { href: url, download: `horas-${month.label.replaceAll(' ', '-')}.csv` });
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** @param {import('#app/lib/hours-report.js').HoursMonth[]} months @param {number} start */
function openMonth(months, start) {
  const body = openDetail(`Detalle de horas · ${months[start].label}`, { wide: true });
  const select = /** @type {HTMLSelectElement} */ (
    el('select', { 'aria-label': 'Mes' }, ...months.map((m, i) => el('option', { value: String(i), text: m.label })))
  );
  const totals = el('div', { class: 'hours-totals' });
  const rows = el('tbody');
  const title = /** @type {HTMLElement} */ (document.getElementById('detail-dialog-title'));
  const csv = el('button', { type: 'button', class: 'btn', text: 'Descargar CSV' });
  body.append(
    el('p', { class: 'hs', text: 'Proyectos que componen las horas del mes seleccionado.' }),
    el('div', { class: 'hours-controls' }, el('label', {}, 'Mes ', select), csv),
    totals,
    el('div', { class: 'table-scroll' }, el('table', {}, el('thead', {}, el('tr', {}, ...['ID / Proyecto', 'Cuenta', 'Servicio', 'Presupuesto proyecto', 'Facturables', 'Inv. operativa', 'Inv. comercial', 'Total'].map((h) => el('th', { scope: 'col', text: h })))), rows)),
    el('p', { class: 'hs', text: 'Cada registro se cuenta una vez: operativa, comercial y después facturable. Otras horas no facturables no se incluyen.' }),
  );

  function fill() {
    const month = months[Number(select.value)];
    title.textContent = `Detalle de horas · ${month.label}`;
    totals.replaceChildren(
      ...[['Total', month.total], ...HOUR_KEYS.map((key, i) => [LABELS[i], month[key]])].map(([label, value]) => el('span', {}, `${label}`, el('b', { text: hours(/** @type {number} */ (value)) }))),
    );
    const projects = [...month.projects].sort((a, b) => b.total - a.total);
    rows.replaceChildren(
      ...(projects.length
        ? projects.map((p) =>
            el(
              'tr',
              {},
              el('td', {}, p.name, el('small', { text: p.id })),
              el('td', { text: p.client || 'Sin cuenta' }),
              el('td', { text: p.service || '—' }),
              el('td', { text: p.project_budget == null ? 'Sin presupuesto' : hours(p.project_budget) }),
              ...HOUR_KEYS.map((key) => el('td', { text: hours(p[key]) })),
              el('td', { text: hours(p.total) }),
            ),
          )
        : [el('tr', {}, el('td', { colspan: 8, text: 'Sin registros en estas categorías.' }))]),
    );
  }
  select.value = String(start);
  select.addEventListener('change', fill);
  csv.addEventListener('click', () => download(months[Number(select.value)]));
  fill();
}

/**
 * @param {import('#app/lib/hours-report.js').HoursMonth[]} months
 * @param {HTMLElement} tooltip
 */
function chart(months, tooltip) {
  const { top, ticks } = hoursScale(months);
  const node = svg('svg', { id: 'hours-chart', viewBox: '0 0 720 260', role: 'group', 'aria-label': 'Consumo de horas por mes. Selecciona un mes para ver sus proyectos.' });
  ticks.forEach((tick, n) => {
    const y = 215 - n * 45;
    node.append(svg('line', { class: 'grid', x1: 56, x2: 704, y1: y, y2: y }), svg('text', { class: 'axis', x: 48, y: y + 4, 'text-anchor': 'end' }, formatNumber(tick, 0)));
  });
  node.append(svg('text', { class: 'axis', x: 12, y: 135, transform: 'rotate(-90 12 135)' }, 'Horas'));
  months.forEach((month, index) => {
    const x = 74 + index * 105;
    const group = svg('g', { tabindex: 0, role: 'button', class: 'hours-bar', 'aria-label': `${month.label}: ${hours(month.total)}. Ver proyectos` });
    const planned = ((month.budget || 0) / top) * 180;
    group.append(svg('rect', { class: 'hit', x: x - 4, y: 25, width: 86, height: 200, rx: 8 }), svg('rect', { class: 'planned', x, y: 215 - planned, width: 36, height: planned, rx: 5 }), svg('text', { class: 'value', x: x + 18, y: Math.max(20, 207 - planned), 'text-anchor': 'middle' }, hours(month.budget)));
    let y = 215;
    HOUR_KEYS.forEach((key, i) => {
      if (month[key] <= 0) return;
      const height = (month[key] / top) * 180;
      y -= height;
      group.append(svg('rect', { class: `k${i}`, x: x + 42, y, width: 36, height }));
    });
    group.append(svg('text', { class: 'value strong', x: x + 60, y: Math.max(20, y - 8), 'text-anchor': 'middle' }, hours(month.total)), svg('text', { class: 'axis', x: x + 39, y: 240, 'text-anchor': 'middle' }, month.label));
    const show = () => {
      tooltip.replaceChildren(
        el('small', { text: month.label }),
        el('b', { text: hours(month.total) }),
        ...HOUR_KEYS.map((key, i) => el('div', {}, el('i', { class: `k${i}` }), el('span', { text: LABELS[i] }), el('strong', { text: `${hours(month[key])} (${month.total ? Math.round((month[key] / month.total) * 100) : 0}%)` }))),
        el('div', { text: `Presupuesto: ${hours(month.budget)}${month.budget_missing ? ` · ${month.budget_missing} sin presupuesto` : ''}` }),
      );
      tooltip.hidden = false;
    };
    const hide = () => (tooltip.hidden = true);
    group.addEventListener('mouseenter', show);
    group.addEventListener('focus', show);
    group.addEventListener('mouseleave', hide);
    group.addEventListener('blur', hide);
    group.addEventListener('click', () => (hide(), openMonth(months, index)));
    group.addEventListener('keydown', (/** @type {Event} */ event) => {
      const key = /** @type {KeyboardEvent} */ (event).key;
      if (key === 'Enter' || key === ' ') {
        event.preventDefault();
        hide();
        openMonth(months, index);
      }
    });
    node.append(group);
  });
  return node;
}

/**
 * @param {HTMLElement} container
 * @param {string} name
 * @param {any} data La seccion `hours` del contrato.
 */
export function renderHours(container, name, data) {
  const heading = (/** @type {Node[]} */ ...extra) => el('div', { class: 'hours-heading' }, el('div', {}, el('h2', { text: 'Consumo de horas por mes · últimos 6 meses' }), ...extra));
  if (data.state === 'pending') {
    container.replaceChildren(el('div', { class: 'card hours-card' }, heading(), el('div', { class: 'cargando', role: 'status', text: 'Cargando consumo desde Clockify…' })));
    return;
  }
  if (data.state === 'unavailable') {
    container.replaceChildren(el('div', { class: 'card hours-card' }, heading(), el('div', { class: 'vacio', text: `No se pudo completar la consulta de Clockify. ${data.error}` })));
    return;
  }
  const tooltip = el('div', { class: 'hours-tooltip', id: 'hours-tooltip', hidden: true });
  const months = data.months;
  const detail = el('button', { type: 'button', class: 'btn', id: 'hours-detail', text: 'Ver detalle de horas →', onclick: () => openMonth(months, months.length - 1) });
  const legend = el(
    'div',
    { class: 'hours-legend' },
    el('div', {}, el('b', { text: 'Presupuestado' }), el('span', {}, el('i', { class: 'planned' }), 'Horas planeadas (prorrateadas)')),
    el('div', {}, el('b', { text: 'Consumido (desglose)' }), el('div', { class: 'consumed' }, ...LABELS.map((label, i) => el('span', {}, el('i', { class: `k${i}` }), label)))),
  );
  container.replaceChildren(
    el(
      'div',
      { class: 'card hours-card' },
      el('div', { class: 'hours-heading' }, el('div', {}, el('h2', { text: 'Consumo de horas por mes · últimos 6 meses' }), el('div', { class: 'hs', text: `Horas de los proyectos de ${name}. El mes actual está en curso.` })), detail),
      ...(data.complete ? [] : [el('div', { class: 'err', role: 'alert', text: `Algunos proyectos no tienen horas en Clockify y no están en esta gráfica. ${data.error}` })]),
      el('div', { class: 'hours-plot' }, chart(months, tooltip), tooltip),
      legend,
      el('p', { class: 'hs', text: 'Selecciona un mes para ver sus proyectos. Presupuesto distribuido por días de vigencia; mes actual hasta hoy. Incluye proyectos actuales y cerrados.' }),
      ...(data.has_data ? [] : [el('p', { class: 'hs', text: 'Sin horas registradas en estas categorías durante el período.' })]),
    ),
  );
}
