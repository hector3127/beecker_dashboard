// @ts-check
// Consumo de horas de los ultimos seis meses: grafica, detalle y CSV.
import { el, svg } from '#app/lib/dom.js';
import { detailDialog } from './hours_detail.js';

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
function chart(months, tooltip, open, mode = 'hours') {
  const percentage=mode==='percent';
  const amount=(month,key)=>percentage?(month.budget>0?Number(month[key]||0)/month.budget*100:0):Number(month[key]||0);
  const caption=(month,key)=>percentage?(month.budget>0?`${amount(month,key).toLocaleString('es-MX',{maximumFractionDigits:1})}%`:'—'):hours(month[key]);
  const root = svg('svg', { id: 'hours-chart', viewBox: '0 0 720 260', role: 'group', 'aria-label': 'Consumo de horas por mes. Selecciona un mes para ver sus proyectos.' });
  root.append(svg('defs',{},...['#d8d0ff',...COLORS].map((color,index)=>svg('linearGradient',{id:`dm-hours-cylinder-${index}`,x1:0,y1:0,x2:1,y2:0},svg('stop',{offset:'0%','stop-color':color}),svg('stop',{offset:'35%','stop-color':color,'stop-opacity':'.7'}),svg('stop',{offset:'100%','stop-color':color})))));
  const limit = Math.max(1, ...months.map((/** @type {any} */ m) => Math.max(amount(m,'total'),amount(m,'budget'))));
  const step = Math.pow(10, Math.floor(Math.log10(limit))) / 2;
  const top = Math.ceil(limit / step) * step;
  for (let tick = 0; tick <= 4; tick++) {
    const y = 215 - tick * 45;
    root.append(
      svg('line', { x1: 56, x2: 704, y1: y, y2: y, stroke: '#e4def4', 'stroke-dasharray': '3 4' }),
      svg('text', { x: 48, y: y + 4, 'text-anchor': 'end', fill: '#8a7eae', 'font-size': 10 }, ((top * tick) / 4).toLocaleString('es-MX', { maximumFractionDigits: 0 })+(percentage?'%':'')),
    );
  }
  root.append(svg('text', { x: 12, y: 135, fill: '#8a7eae', 'font-size': 11, transform: 'rotate(-90 12 135)' }, percentage?'% del presupuesto':'Horas'));

  months.forEach((/** @type {any} */ month, /** @type {number} */ index) => {
    const slot=648/Math.max(1,months.length);
    const x = 56+index*slot+(slot-80)/2;
    const group = svg('g', { tabindex: 0, role: 'button', 'aria-label': `${month.label}: ${hours(month.total)}. Ver proyectos` });
    group.style.cursor = 'pointer'; // CSSOM: sin atributo style
    group.append(svg('rect', {class:'dm-hours-focus', x: x - 4, y: 15, width: 86, height: 235, fill: 'transparent', rx: 10 }));
    const planned = (amount(month,'budget') / top) * 180;
    group.append(
      svg('rect', { x, y: 215 - planned, width: 36, height: planned, fill: 'url(#dm-hours-cylinder-0)', rx: 5 }),
      svg('ellipse',{cx:x+18,cy:215-planned,rx:18,ry:4,fill:'#e6deff'}),
      svg('text', { x: x + 18, y: Math.max(20, 203 - planned), 'text-anchor': 'middle', fill: '#20145e', 'font-size': 9 }, caption(month,'budget')),
    );
    let y = 215;
    KEYS.forEach((key, i) => {
      if (month[key] <= 0) return;
      const height = (amount(month,key) / top) * 180;
      y -= height;
      group.append(svg('rect', { x: x + 42, y, width: 36, height, fill: `url(#dm-hours-cylinder-${i+1})` }),svg('ellipse',{cx:x+60,cy:y,rx:18,ry:4,fill:COLORS[i]}));
    });
    group.append(
      svg('text', { x: x + 60, y: Math.max(20, y - 8), 'text-anchor': 'middle', fill: '#20145e', 'font-size': 9, 'font-weight': 700 }, caption(month,'total')),
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
  const detail = detailDialog(months, csvRows, csvCell);
  let mode='hours',range=6;
  const plot=el('div',{class:'hours-plot'});
  const modeHours=el('button',{type:'button',id:'hours-view-hours','aria-pressed':'true',text:'Horas'});
  const modePercent=el('button',{type:'button',id:'hours-view-percent','aria-pressed':'false',text:'% de uso',title:'Horas consumidas respecto al presupuesto prorrateado del mes',disabled:!months.some(month=>month.budget>0)});
  const rangeSelect=el('select',{id:'hours-range','aria-label':'Meses de consumo'},el('option',{value:'3',text:'Últimos 3 meses'}),el('option',{value:'6',text:'Últimos 6 meses'}));
  rangeSelect.value='6';
  function update(){
    const visible=months.slice(-range);
    tooltip.hidden=true;
    plot.replaceChildren(chart(visible,tooltip,index=>{tooltip.hidden=true;detail.open(months.indexOf(visible[index]));},mode),tooltip);
    modeHours.setAttribute('aria-pressed',String(mode==='hours'));modePercent.setAttribute('aria-pressed',String(mode==='percent'));
  }
  modeHours.addEventListener('click',()=>{mode='hours';update();});
  modePercent.addEventListener('click',()=>{mode='percent';update();});
  rangeSelect.addEventListener('change',()=>{range=Number(rangeSelect.value);update();});
  const chartControls=el('div',{class:'dm-hours-controls'},el('div',{class:'dm-hours-mode'},modeHours,modePercent),rangeSelect);

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
      ...(months.length ? [chartControls,el('button', { type: 'button', class: 'hours-action', id: 'hours-detail', text: 'Ver detalle de horas →', onclick: () => detail.open(months.length - 1) })] : []),
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
    plot,
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
  update();
  const action=card.querySelector('#hours-detail');
  const footer=el('div',{class:'dm-hours-footer'},el('span',{text:'ⓘ Selecciona un mes para ver sus proyectos. % de uso se calcula sobre el presupuesto del mes.'}));
  if(action)footer.append(action);
  card.append(footer);
  return section;
}
