// @ts-check
// Facturabilidad global por mes: cifra del mes, distancia a la meta y barras
// que se pueden elegir. Elegir un mes no pide datos: usa los ya cargados.
import { percentText } from '#app/lib/charts.js';
import { el, svg } from '#app/lib/dom.js';

/**
 * @typedef {object} BillingMonth
 * @property {string} month
 * @property {string} label
 * @property {string} month_label
 * @property {number | null} global_percent
 * @property {number | null} fixed_percent
 * @property {number | null} variable_percent
 */

let chartSequence=0;

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
 * @param {{selectedMonth?: string|null, onSelect?: (month: string) => void}} [options]
 * @returns {HTMLElement}
 */
export function createBillingChart(data, options = {}) {
  const gradientId=`billing-selected-${++chartSequence}`;
  const backgroundId=`billing-highlight-${chartSequence}`;
  const definitions=svg('defs',{},
    svg('linearGradient',{id:gradientId,x1:0,y1:0,x2:0,y2:1},
      svg('stop',{offset:'0%','stop-color':'#8848f6'}),svg('stop',{offset:'100%','stop-color':'#6033d5'})),
    svg('linearGradient',{id:backgroundId,x1:0,y1:0,x2:0,y2:1},
      svg('stop',{offset:'0%','stop-color':'#eee6ff','stop-opacity':'.65'}),svg('stop',{offset:'100%','stop-color':'#f5efff','stop-opacity':'.7'}))
  );
  const months = data.months;
  const context = {target:data.target,latestMonth:data.month,monthClosed:data.month_closed};
  const value=el('div',{class:'billing-value','aria-live':'polite'});
  const gap=el('div',{class:'billing-gap'});
  const fixed=el('span',{class:'billing-chip',title:'Trabajo fijo: horas AER ÷ capacidad'});
  const variable=el('span',{class:'billing-chip',title:'Trabajo variable: TYM, IXB, SaaS y RaaS ÷ capacidad que queda'});
  const label=el('div',{class:'billing-label'});
  const groups=new Map();
  function select(month){
    const view=describeMonth(month,context);
    value.textContent=view.value;fixed.textContent=view.fixed;variable.textContent=view.variable;
    gap.textContent=view.gapText;gap.classList.toggle('is-down',view.gap!==null&&view.gap<0);gap.classList.toggle('is-none',view.gap===null);
    label.textContent=view.label;
    for(const [key,group] of groups){group.setAttribute('aria-pressed',String(key===month.month));group.classList.toggle('is-selected',key===month.month);}
    options.onSelect?.(month.month);
  }
  const max=Math.max(100,...months.map(month=>Number(month.global_percent)||0),Number(data.target)||0);
  const scale=Math.ceil(max/20)*20;
  const left=43,right=708,top=28,bottom=210;
  const y=value=>bottom-Math.max(0,value)/scale*(bottom-top);
  const axes=[];
  for(let i=0;i<=5;i++){
    const tick=scale/5*i;
    axes.push(svg('line',{class:'billing-gridline',x1:left,y1:y(tick),x2:right,y2:y(tick)}));
    axes.push(svg('text',{class:'billing-axis-label',x:left-9,y:y(tick)+4,'text-anchor':'end'},`${tick}%`));
  }
  const target=Number(data.target);
  if(Number.isFinite(target))axes.push(svg('line',{class:'billing-target-line',x1:left,y1:y(target),x2:right,y2:y(target),'data-target':target}));
  const slot=(right-left)/Math.max(1,months.length);
  const bars=months.map((month,index)=>{
    const x=left+slot*index+slot*.17,width=slot*.66,center=x+width/2;
    const known=month.global_percent!==null&&Number.isFinite(month.global_percent);
    const barY=known?y(month.global_percent):bottom;
    const text=percentText(month.global_percent);
    const group=svg('g',{class:'billing-bar',role:'button',tabindex:0,'aria-pressed':'false','aria-label':`${month.month_label}: ${text}`},
      svg('title',{},`${month.label}: ${text} de facturabilidad global`),
      svg('rect',{class:'billing-selection-bg',x:left+slot*index+slot*.065,y:2,width:slot*.87,height:241,rx:12,fill:`url(#${backgroundId})`}),
      svg('rect',{class:'billing-rect',x,y:barY,width,height:bottom-barY,rx:7}),
      svg('rect',{class:'billing-selected-bar',x,y:barY,width,height:bottom-barY,rx:7,fill:`url(#${gradientId})`}),
      svg('text',{class:'billing-text',x:center,y:Math.max(15,barY-9),'text-anchor':'middle'},text),
      svg('text',{class:'billing-month',x:center,y:231,'text-anchor':'middle'},month.label),
      svg('rect',{x,y:0,width,height:240,fill:'transparent'})
    );
    groups.set(month.month,group);group.addEventListener('click',()=>select(month));
    group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(month);}});
    return group;
  });
  const start=months.find(month=>month.month===options.selectedMonth)||months.at(-1);
  if(start)select(start);
  else{value.textContent='—';gap.textContent='Sin datos para comparar con la meta';gap.classList.add('is-none');fixed.textContent='AER —';variable.textContent='PRJ —';}
  return el('div',{class:'billing'},
    el('div',{class:'billing-main'},
      el('div',{class:'billing-title'},'Facturabilidad global',el('span',{class:'billing-info',title:'Horas facturables respecto a la capacidad del equipo. La meta y los datos provienen del corte operativo.',text:'ⓘ'})),
      value,gap,el('div',{class:'ops-muted',text:`Meta: ${Math.round(data.target)}% de la capacidad`}),
      el('div',{class:'billing-chips'},fixed,variable),label),
    el('div',{class:'billing-chart'},
      el('div',{class:'billing-chart-header'},el('div',{class:'billing-chart-title',text:'Facturabilidad global por mes'}),
        el('div',{class:'billing-legend'},el('span',{class:'billing-legend-series',text:'Facturabilidad'}),el('span',{class:'billing-legend-target',text:`Meta (${data.target}%)`}))
      ),
      bars.length?el('div',{class:'billing-plot-scroll',tabindex:0,role:'region','aria-label':'Gráfica mensual; desplaza para ver todos los meses'},svg('svg',{viewBox:'0 0 720 246',width:'100%',class:'billing-svg',role:'group','aria-label':'Selecciona un mes para ver su facturabilidad'},definitions,...axes,...bars)):el('p',{class:'ops-muted',text:'Sin meses que mostrar.'}),
      data.errors.length?el('div',{class:'billing-errors',text:`Sin datos completos: ${data.errors.join('; ')}`}):''
    )
  );
}
