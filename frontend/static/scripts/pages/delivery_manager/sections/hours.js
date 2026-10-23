// @ts-check
// Consumo de horas de los ultimos seis meses: grafica, detalle y CSV.
import { el, svg } from '#app/lib/dom.js';

const COLORS = ['#6347ed', '#18ad78', '#f5b326'];
const KEYS = ['billable', 'operational', 'commercial'];
const LABELS = ['Facturables', 'Inversión operativa', 'Inversión comercial'];
const TITLE = 'Consumo de horas por mes · últimos 6 meses';

/** @param {unknown} value */
const hours = (value) => `${Number(value || 0).toLocaleString('es-MX', { maximumFractionDigits: 1 })} h`;

/** Celda CSV segura: un texto que empieza con =, +, @ o - no se ejecuta como formula. @param {unknown} value */
export function csvCell(value) {
  let text = String(value ?? '');
  if (/^[=+@-]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

/** @param {any} month */
export function csvRows(month) {
  return [
    ['ID', 'Proyecto', 'Cuenta', 'Servicio', 'Presupuesto proyecto', 'Facturables', 'Inv. operativa', 'Inv. comercial', 'Total'],
    ...month.projects.map((/** @type {any} */ p) => [p.id, p.name, p.client, p.service, p.project_budget, p.billable, p.operational, p.commercial, p.total]),
  ];
}

/** @param {string} message */
const pending = (message) => el('section', { class: 'monthly-section', id: 'dm-monthly' }, el('div', { class: 'card hours-card' }, el('h2', { text: TITLE }), el('div', { class: 'vacio', role: 'status', text: message })));

export const loadingHours = () => pending('Cargando consumo desde Clockify…');

/** @param {any} months @param {HTMLElement} tooltip @param {(index: number) => void} open */
function chart(months, tooltip, open) {
  const root = svg('svg', { id: 'hours-chart', viewBox: '0 0 720 260', role: 'group', 'aria-label': 'Consumo de horas por mes. Selecciona un mes para ver sus proyectos.' });
  const limit = Math.max(1, ...months.map((/** @type {any} */ m) => Math.max(m.total, m.budget || 0)));
  const step = Math.pow(10, Math.floor(Math.log10(limit))) / 2;
  const top = Math.ceil(limit / step) * step;
  for (let tick = 0; tick <= 4; tick++) {
    const y = 215 - tick * 45;
    root.append(
      svg('line', { x1: 56, x2: 704, y1: y, y2: y, stroke: '#e4def4', 'stroke-dasharray': '3 4' }),
      svg('text', { x: 48, y: y + 4, 'text-anchor': 'end', fill: '#8a7eae', 'font-size': 10 }, ((top * tick) / 4).toLocaleString('es-MX', { maximumFractionDigits: 0 })),
    );
  }
  root.append(svg('text', { x: 12, y: 135, fill: '#8a7eae', 'font-size': 11, transform: 'rotate(-90 12 135)' }, 'Horas'));

  months.forEach((/** @type {any} */ month, /** @type {number} */ index) => {
    const x = 74 + index * 105;
    const group = svg('g', { tabindex: 0, role: 'button', 'aria-label': `${month.label}: ${hours(month.total)}. Ver proyectos` });
    group.style.cursor = 'pointer'; // CSSOM: sin atributo style
    group.append(svg('rect', { x: x - 4, y: 25, width: 86, height: 200, fill: 'transparent', rx: 8 }));
    const planned = ((month.budget || 0) / top) * 180;
    group.append(
      svg('rect', { x, y: 215 - planned, width: 36, height: planned, fill: '#d8d0ff', rx: 5 }),
      svg('text', { x: x + 18, y: Math.max(20, 207 - planned), 'text-anchor': 'middle', fill: '#20145e', 'font-size': 9 }, hours(month.budget)),
    );
    let y = 215;
    KEYS.forEach((key, i) => {
      if (month[key] <= 0) return;
      const height = (month[key] / top) * 180;
      y -= height;
      group.append(svg('rect', { x: x + 42, y, width: 36, height, fill: COLORS[i] }));
    });
    group.append(
      svg('text', { x: x + 60, y: Math.max(20, y - 8), 'text-anchor': 'middle', fill: '#20145e', 'font-size': 9, 'font-weight': 700 }, hours(month.total)),
      svg('text', { x: x + 39, y: 240, 'text-anchor': 'middle', fill: '#8a7eae', 'font-size': 11 }, month.label),
    );
    const show = () => {
      const rows = KEYS.map((key, i) => {
        const share = month.total ? Math.round((month[key] / month.total) * 100) : 0;
        const dot = el('i');
        dot.style.background = COLORS[i];
        return el('div', {}, dot, el('span', { text: LABELS[i] }), el('strong', { text: `${hours(month[key])} (${share}%)` }));
      });
      const plan = el('div', { text: `Presupuesto: ${hours(month.budget)}${month.budget_missing ? ` · ${month.budget_missing} sin presupuesto` : ''}` });
      tooltip.replaceChildren(el('small', { text: month.label }), el('b', { text: hours(month.total) }), ...rows, plan);
      tooltip.hidden = false;
    };
    const hide = () => {
      tooltip.hidden = true;
    };
    group.addEventListener('mouseenter', show);
    group.addEventListener('focus', show);
    group.addEventListener('mouseleave', hide);
    group.addEventListener('blur', hide);
    group.addEventListener('click', () => open(index));
    group.addEventListener('keydown', (event) => {
      const key = /** @type {KeyboardEvent} */ (event).key;
      if (key === 'Enter' || key === ' ') {
        event.preventDefault();
        open(index);
      }
    });
    root.append(group);
  });
  return root;
}

/** @param {any} months */
function detailDialog(months) {
  const select = /** @type {HTMLSelectElement} */ (
    el('select', { id: 'hours-month' }, ...months.map((/** @type {any} */ m, /** @type {number} */ i) => el('option', { value: i, text: m.label })))
  );
  const title = el('h2', { id: 'hours-modal-title', text: 'Detalle de horas' });
  const totals = el('div', { id: 'hours-totals', class: 'hours-totals' });
  const body = el('tbody', { id: 'hours-projects' });
  const heads = ['ID / Proyecto', 'Cuenta', 'Servicio', 'Presupuesto proyecto', 'Facturables', 'Inv. operativa', 'Inv. comercial', 'Total'];
  const dialog = /** @type {HTMLDialogElement} */ (
    el(
      'dialog',
      { id: 'hours-modal', 'aria-labelledby': 'hours-modal-title' },
      el(
        'div',
        { class: 'hours-heading' },
        el('div', {}, title, el('p', { class: 'hs', text: 'Proyectos que componen las horas del mes seleccionado.' })),
        el('button', { type: 'button', id: 'hours-close', 'aria-label': 'Cerrar detalle', text: '×', onclick: () => dialog.close() }),
      ),
      el('div', { class: 'hours-controls' }, el('label', {}, 'Mes ', select), el('button', { type: 'button', class: 'hours-action', id: 'hours-download', text: 'Descargar CSV' })),
      totals,
      el('div', { class: 'table-scroll' }, el('table', {}, el('thead', {}, el('tr', {}, ...heads.map((text) => el('th', { text })))), body)),
      el('p', { class: 'hs', text: 'Cada registro se cuenta una vez: operativa, comercial y después facturable. Otras horas no facturables no se incluyen.' }),
    )
  );

  /** @param {number} index */
  function fill(index) {
    const month = months[index];
    select.value = String(index);
    title.textContent = `Detalle de horas · ${month.label}`;
    totals.replaceChildren(
      ...[['Total', month.total], ...KEYS.map((key, i) => [LABELS[i], month[key]])].map(([label, amount]) => el('span', {}, label, el('b', { text: hours(amount) }))),
    );
    const rows = [...month.projects]
      .sort((a, b) => b.total - a.total)
      .map((project) => {
        const cells = [project.name, project.client || 'Sin cuenta', project.service || '—', project.project_budget == null ? 'Sin presupuesto' : hours(project.project_budget), ...KEYS.map((key) => hours(project[key])), hours(project.total)];
        return el('tr', {}, ...cells.map((text, i) => el('td', {}, text, ...(i === 0 ? [el('small', { text: project.id })] : []))));
      });
    body.replaceChildren(...(rows.length ? rows : [el('tr', {}, el('td', { colspan: 8, text: 'Sin registros en estas categorías.' }))]));
  }

  select.addEventListener('change', () => fill(Number(select.value)));
  dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    const { clientX: x, clientY: y } = /** @type {MouseEvent} */ (event);
    if (x < box.left || x > box.right || y < box.top || y > box.bottom) dialog.close();
  });
  dialog.querySelector('#hours-download')?.addEventListener('click', () => {
    const month = months[Number(select.value)];
    const text = csvRows(month).map((row) => row.map(csvCell).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([`﻿${text}`], { type: 'text/csv;charset=utf-8' }));
    const link = el('a', { href: url, download: `horas-${month.label.replaceAll(' ', '-')}.csv` });
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  return {
    dialog,
    /** @param {number} index */
    open(index) {
      fill(index);
      if (!dialog.open) dialog.showModal();
    },
  };
}

/**
 * @param {any} data La seccion `hours` de la API y el nombre del DM.
 * @param {string} name
 */
export function renderHours(data, name) {
  const section = el('section', { class: 'monthly-section', id: 'dm-monthly' });
  const months = data.months;
  const card = el('div', { class: 'card hours-card' });
  section.append(card);
  const tooltip = el('div', { id: 'hours-tooltip', class: 'hours-tooltip', hidden: true });
  const detail = detailDialog(months);
  const legend = (/** @type {string} */ color, /** @type {string} */ text) => {
    const dot = el('i');
    dot.style.background = color;
    return el('span', {}, dot, text);
  };
  card.append(
    el(
      'div',
      { class: 'hours-heading' },
      el('div', {}, el('h2', { text: TITLE }), el('div', { class: 'hs', text: `Horas de los proyectos de ${name}. El mes actual está en curso.` })),
      ...(months.length ? [el('button', { type: 'button', class: 'hours-action', id: 'hours-detail', text: 'Ver detalle de horas →', onclick: () => detail.open(months.length - 1) })] : []),
    ),
  );
  if (!months.length) {
    card.append(el('div', { class: 'vacio', text: `No se pudo completar la consulta de Clockify. ${data.error}` }));
    return section;
  }
  if (!data.complete) {
    card.append(
      el('div', { class: 'err', role: 'alert', style: { margin: '12px 0 0', padding: '10px 14px', borderRadius: '10px', background: '#FFF3D6', color: '#7A4D00', fontSize: '13px' }, text: `Algunos proyectos no tienen horas en Clockify y no están en esta gráfica. ${data.error}` }),
    );
  }
  card.append(
    el('div', { class: 'hours-plot' }, chart(months, tooltip, (index) => {
      tooltip.hidden = true;
      detail.open(index);
    }), tooltip),
    el(
      'div',
      { class: 'monthly-legend comparison-legend' },
      el('div', {}, el('b', { text: 'Presupuestado' }), legend('#d8d0ff', 'Horas planeadas (prorrateadas)')),
      el('div', {}, el('b', {}, 'Consumido ', el('small', { text: '(desglose)' })), el('div', { class: 'consumed-legend' }, legend('#6347ed', 'Facturables'), legend('#18ad78', 'Inversión operativa'), legend('#f5b326', 'Inversión comercial'))),
    ),
    el('p', { class: 'hs', text: 'Selecciona un mes para ver sus proyectos. Presupuesto distribuido por días de vigencia; mes actual hasta hoy. Incluye proyectos actuales y cerrados.' }),
    ...(data.has_data ? [] : [el('p', { class: 'hs', text: 'Sin horas registradas en estas categorías durante el período.' })]),
    detail.dialog,
  );
  return section;
}
