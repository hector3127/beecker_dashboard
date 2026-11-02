import { el } from '#app/lib/dom.js';
import { icon } from './ixs_icons.js';
import { actionDistribution } from './actions_distribution.js';
const node=(tag,cls,...children)=>el(tag,cls?{class:cls}:{},...children.flat().filter(x=>x!=null));
const div=(cls,...children)=>node('div',cls,...children);
export function actionDistributionView(m) {
  const buckets=actionDistribution(m),total=m.filas.length;
  let angle=0;
  const stops=buckets.map(b=>{const start=angle;angle+=total?100*b.count/total:0;return `${b.color} ${start}% ${angle}%`;});
  const donut=div('action-state-donut',div('',node('b','',String(total)),node('small','','Acciones')));
  donut.style.background=total?`conic-gradient(${stops.join(',')})`:'#ede6f8';
  return div('aer-action-strip',node('h4','',icon('donut'),' Distribución por estado'),
    div('action-state-layout',donut,div('action-state-legend',...buckets.map(b=>{
      const dot=node('i','');dot.style.background=b.color;
      return div('',dot,node('span','',b.label),node('b','',String(b.count)),node('small','',`${total?(100*b.count/total).toLocaleString('es-MX',{maximumFractionDigits:1}):0}%`));
    }))));
}
export function actionResponsibleView(m) {
  const rows=Object.entries(m.respCount).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
  const max=Math.max(1,...rows.map(r=>r[1]));
  return div('aer-action-strip',node('h4','',icon('people'),' Responsables con acciones'),
    div('action-responsible-layout',div('action-responsible-total',node('b','',String(rows.length)),node('small','','Responsables con acciones')),
      div('action-responsible-list',...(rows.length?rows.map(([name,count])=>{
        const fill=node('i','');fill.style.width=`${100*count/max}%`;
        return div('action-responsible-row',node('span','action-avatar',name.trim().split(/\s+/).slice(0,2).map(p=>p[0]).join('').toUpperCase()),node('span','action-responsible-name',name),div('action-responsible-track',fill),node('b','',String(count)));
      }):[node('p','','Sin responsables registrados.')]))));
}
export function actionWeeklyView(m) {
  const make=(tag,attrs={},text)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(text!=null)n.textContent=String(text);return n;};
  const svg=make('svg',{viewBox:'0 0 460 152',role:'img','aria-label':'Acciones previstas por semana',class:'action-weekly-svg'});
  const max=Math.max(1,...m.weeks.map(w=>w.cnt));
  const points=m.weeks.map((w,i)=>[32+i*99,122-w.cnt/max*74]);
  const defs=make('defs'),gradient=make('linearGradient',{id:'action-weekly-fill',x1:0,y1:0,x2:0,y2:1});
  gradient.append(make('stop',{offset:'0%','stop-color':'#a668ff','stop-opacity':'.35'}),make('stop',{offset:'100%','stop-color':'#b992ff','stop-opacity':'.05'}));defs.append(gradient);svg.append(defs);
  svg.append(make('path',{d:`M${points[0][0]},122 L${points.map(p=>p.join(',')).join(' L')} L${points.at(-1)[0]},122 Z`,fill:'url(#action-weekly-fill)'}),make('polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:'#8627f4','stroke-width':2}));
  m.weeks.forEach((w,i)=>{const [x,y]=points[i],date=new Date(w.iso+'T12:00:00').toLocaleDateString('es-MX',{day:'2-digit',month:'short'});
    svg.append(make('line',{x1:x,x2:x,y1:y,y2:122,stroke:'#ece2fa'}),make('circle',{cx:x,cy:y,r:5,fill:'#8123eb',stroke:'#fff','stroke-width':2}),make('rect',{x:x-14,y:y-32,width:28,height:23,rx:7,fill:'#efe4ff'}),make('text',{x,y:y-16,'text-anchor':'middle',class:'value'},w.cnt),make('text',{x,y:144,'text-anchor':'middle'},date));
  });
  return div('aer-action-strip',node('h4','',icon('chart'),' Seguimiento semanal'),node('small','action-weekly-note','Acciones por fecha de seguimiento'),svg);
}
