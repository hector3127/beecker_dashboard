// Facturabilidad: visualización local de los datos originales del periodo.
import { el, svg } from '#app/lib/dom.js';
const number=value=>{if(value===''||value==null)return null;const n=Number(String(value).replace(',','.'));return Number.isFinite(n)?n:null;};
const fmt=(value,digits=1)=>value==null||!Number.isFinite(Number(value))?'—':Number(value).toLocaleString('es-MX',{maximumFractionDigits:digits});
function icon(kind){const paths={bars:'M5 20V12M12 20V4M19 20V9',file:'M5 2h9l5 5v15H5zM14 2v6h5M8 12h8M8 16h6',globe:'M3 12h18M12 3c-6 4-6 14 0 18M12 3c6 4 6 14 0 18'};return el('span',{class:'bill-reference-icon'},svg('svg',{viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':1.8,'stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true'},...(kind==='globe'?[svg('circle',{cx:12,cy:12,r:9})]:[]),svg('path',{d:paths[kind]})));}
function sparkline(values,index){const present=values.filter(value=>value!==null);if(!present.length)return null;const min=Math.min(...present),max=Math.max(...present);const points=values.map((value,i)=>value===null?null:[i*140/Math.max(values.length-1,1),57-(value-min)/Math.max(max-min,1)*45]).filter(Boolean);if(!points.length)return null;const d=points.map((point,i)=>`${i?'L':'M'}${point[0]},${point[1]}`).join(' ');const last=points.at(-1);return svg('svg',{class:'bill-sparkline',viewBox:'0 0 145 66','aria-hidden':'true'},svg('defs',{},svg('linearGradient',{id:`bill-spark-${index}`,x2:0,y2:1},svg('stop',{offset:'0%','stop-color':'currentColor','stop-opacity':'.3'}),svg('stop',{offset:'100%','stop-color':'currentColor','stop-opacity':'0'}))),svg('path',{d:`${d} L${last[0]},66 L${points[0][0]},66Z`,fill:`url(#bill-spark-${index})`}),svg('path',{d,fill:'none',stroke:'currentColor','stroke-width':2,'stroke-linejoin':'round'}),svg('circle',{cx:last[0],cy:last[1],r:3.5,fill:'currentColor',stroke:'#fff','stroke-width':2}));}
export function mountReference(){
 const old=document.querySelector('.bars');if(!old)return;
 const months=[...old.children].map(node=>({month:node.dataset.month,label:node.dataset.label,short:node.lastChild.textContent.trim(),percent:number(node.dataset.percent),fixed:number(node.dataset.fixed),variable:number(node.dataset.variable),fixedPercent:number(node.dataset.fixedPercent),variablePercent:number(node.dataset.variablePercent),selected:node.classList.contains('cu')}));
 const cards=[...document.querySelectorAll('.hero>.kc,.hero>.tot')];
 cards.forEach((card,index)=>{const copy=el('div',{class:'bill-kpi-copy'},...card.childNodes);card.append(icon(['bars','file','globe'][index]),copy);if(index<2){const plot=sparkline(months.map(month=>index?month.variablePercent:month.fixedPercent),index);if(plot)card.append(plot);}else card.append(el('span',{class:'bill-total-decoration','aria-hidden':'true'},el('i'),el('i'),el('i')));});
 const table=document.querySelector('.sc table');table.id='bill-summary';
 [...table.tBodies[0].rows].forEach(row=>{const cell=row.cells[row.cells.length-1],raw=number(cell.textContent.trim().replace('%',''));if(raw===null)return;cell.replaceChildren(el('span',{class:`bill-global-pill ${raw>=70?'good':'warning'}`,text:cell.textContent.trim()}));});
 const section=old.closest('section');section.id='bill-chart-card';section.classList.add('bill-chart-card');
 const title=section.querySelector('h2'),description=section.querySelector('.hs');
 const percent=el('button',{id:'bill-mode-percent',type:'button',text:'% Facturabilidad','aria-pressed':'true'}),hours=el('button',{id:'bill-mode-hours',type:'button',text:'Horas facturadas','aria-pressed':'false'});
 const expand=el('button',{id:'bill-chart-expand',class:'bill-chart-expand',type:'button','aria-label':'Ampliar gráfica','aria-expanded':'false',text:'⤢'});
 const header=el('div',{class:'bill-chart-heading'},icon('globe'),el('div',{class:'bill-chart-heading-copy'},title,description),el('div',{class:'bill-chart-controls'},el('div',{class:'bill-chart-mode'},percent,hours),expand));
 const plot=el('div',{class:'bill-chart-plot'}),aside=el('aside',{class:'bill-chart-aside','aria-live':'polite'}),legend=el('div',{class:'bill-chart-legend'});
 section.replaceChildren(header,el('div',{class:'bill-chart-body'},plot,aside),legend);
 let mode='percent',selected=months.findLastIndex(month=>month.selected);if(selected<0)selected=months.length-1;
 const amount=month=>mode==='percent'?month.percent:month.fixed===null||month.variable===null?null:month.fixed+month.variable;
 function render(){
  percent.setAttribute('aria-pressed',String(mode==='percent'));hours.setAttribute('aria-pressed',String(mode==='hours'));
  const values=months.map(amount),valid=values.filter(value=>value!==null&&Number.isFinite(value)),average=valid.length?valid.reduce((a,b)=>a+b,0)/valid.length:null;
  const top=mode==='percent'?Math.max(100,Math.ceil(Math.max(0,...valid)/25)*25):Math.max(1,Math.ceil(Math.max(0,...valid)/1000)*1000);
  const W=Math.max(700,plot.clientWidth),H=section.classList.contains('bill-chart-expanded')?Math.max(260,window.innerHeight-200):220,base=H-30,height=H-55,start=46,slot=(W-58)/Math.max(1,months.length);
  const root=svg('svg',{id:'bill-chart',viewBox:`0 0 ${W} ${H}`,height:H,role:'group','aria-label':mode==='percent'?'Facturabilidad global por mes':'Horas facturadas por mes'});
  root.append(svg('defs',{},svg('linearGradient',{id:'bill-bar-active',x2:0,y2:1},svg('stop',{offset:'0%','stop-color':'#8d4dff'}),svg('stop',{offset:'100%','stop-color':'#5021d2'}))));
  for(let tick=0;tick<=4;tick++){const y=base-tick/4*height;root.append(svg('line',{x1:start,x2:W-8,y1:y,y2:y,stroke:'#eee8fc','stroke-width':1}),svg('text',{x:start-7,y:y+3,'text-anchor':'end',fill:'#a08ac2','font-size':9},`${fmt(top*tick/4,0)}${mode==='percent'?'%':''}`));}
  months.forEach((month,index)=>{const value=values[index],x=start+index*slot+5,width=slot-10,y=value===null?base:base-Math.max(0,value)/top*height;const group=svg('g',{role:'button',tabindex:0,'aria-label':`${month.label}: ${fmt(value)}${mode==='percent'?'%':' h'}`,'aria-pressed':String(selected===index)});group.append(svg('rect',{class:'bill-chart-focus',x:x-4,y:8,width:width+8,height:H-12,rx:9,fill:'transparent'}),svg('rect',{x,y,width,height:base-y,rx:5,fill:selected===index?'url(#bill-bar-active)':'#d6c7fa'}),svg('text',{x:x+width/2,y:Math.max(20,y-9),'text-anchor':'middle',fill:selected===index?'#6128d0':'#654b8a','font-size':10,'font-weight':600},`${fmt(value)}${value===null?'':mode==='percent'?'%':' h'}`),svg('text',{x:x+width/2,y:base+18,'text-anchor':'middle',fill:selected===index?'#5e24ca':'#9b84bd','font-size':10,'font-weight':selected===index?700:400},month.short));group.append(svg('title',{},`${month.label}: ${fmt(value,2)}${mode==='percent'?'%':' h'}`));const choose=()=>{selected=index;render();};group.addEventListener('click',choose);group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();choose();}});root.append(group);});
  if(average!==null){const y=base-average/top*height;root.append(svg('line',{x1:start,x2:W-8,y1:y,y2:y,stroke:'#be99f6','stroke-dasharray':'4 4','pointer-events':'none'}));}
  plot.replaceChildren(root);
  const current=months[selected],value=values[selected],previous=selected>0?values[selected-1]:null,delta=value!==null&&previous!==null?value-previous:null;
  aside.replaceChildren(el('small',{text:current?.label||'Sin meses'}),el('strong',{text:`${fmt(value,2)}${value===null||value===undefined?'':mode==='percent'?'%':' h'}`}),...(delta===null?[]:[el('span',{class:delta<0?'negative':'positive',text:`${delta<0?'↓':'↑'} ${fmt(Math.abs(delta),2)} ${mode==='percent'?'pp':'h'}`}),el('small',{text:`vs. ${months[selected-1].label.toLowerCase()}`})]));
  legend.replaceChildren(el('span',{class:'bill-legend-bars',text:mode==='percent'?'Facturabilidad global':'Horas facturadas'}),el('span',{class:'bill-legend-average',text:`Promedio mensual (${fmt(average)}${average===null?'':mode==='percent'?'%':' h'})`}));
 }
 percent.addEventListener('click',()=>{mode='percent';render();});hours.addEventListener('click',()=>{mode='hours';render();});
 expand.addEventListener('click',()=>{const expanded=section.classList.toggle('bill-chart-expanded');expand.setAttribute('aria-expanded',String(expanded));expand.setAttribute('aria-label',expanded?'Reducir gráfica':'Ampliar gráfica');render();});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'){section.classList.remove('bill-chart-expanded');expand.setAttribute('aria-expanded','false');expand.setAttribute('aria-label','Ampliar gráfica');render();}});
 render();
 let plotWidth=plot.clientWidth;
 new ResizeObserver(()=>{const width=plot.clientWidth;if(width!==plotWidth){plotWidth=width;render();}}).observe(plot);
}
