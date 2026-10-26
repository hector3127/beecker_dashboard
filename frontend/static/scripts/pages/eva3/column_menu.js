// Menú de columna con borrador local: Cancelar no cambia el filtro aplicado.
import { el } from '#app/lib/dom.js';
export const normalize = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
export function columnColor(cell) {
  for (const [selector,key,label] of [['.hm .cr,.bad,.over,.pd,.critical,.eva4-pill.suspended,.st.sus,.st.dep','red','Rojo'],['.hm .cg,.ok,.finished,.eva4-pill.active','green','Verde'],['.cancelled','red','Rojo'],['.service-aer,.service-pill.raas,.st.dev','blue','Azul'],['.service-tym,.service-pill:not(.raas),.st:not(.sus):not(.dep):not(.dev)','purple','Morado'],['.hm .cy,.eva4-pill.warning','yellow','Amarillo']]) if(cell.matches(selector)||cell.querySelector(selector))return {key,label};
  return {key:'none',label:'Sin color'};
}
export function matchesColumn(raw,value,color,filter) {
  if (!filter) return true;
  if (filter.values && !filter.values.has(raw)) return false;
  if (filter.color && color !== filter.color) return false;
  const {condition:op,first,second} = filter;
  if (!op) return true;
  if(op==='empty')return raw==='';
  if(op==='notempty')return raw!=='';
  if(op==='contains')return normalize(raw).includes(normalize(first));
  if(op==='notcontains')return !normalize(raw).includes(normalize(first));
  if(op==='textis')return normalize(raw)===normalize(first);
  if(op==='textnot')return normalize(raw)!==normalize(first);
  if(value===null || first==='')return false;
  const a=typeof value==='number'?Number(first):first,b=typeof value==='number'?Number(second):second;
  return op==='eq'?value===a:op==='gt'?value>a:op==='gte'?value>=a:op==='lt'?value<a:op==='lte'?value<=a:op==='between'?second!==''&&value>=a&&value<=b:true;
}
export function openColumnMenu({host,trigger,label,type,entries,filter,onApply,onSort,extraConditions=[]}) {
  host.querySelector('.eva3-column-menu')?.remove();
  const values=[...new Set(entries.map(item=>item.raw))].sort((a,b)=>a.localeCompare(b,'es',{numeric:true}));
  let selection=new Set(filter?.values || values);
  const colors=[...new Map(entries.map(item=>[item.color.key,item.color])).values()];
  const search=el('input',{type:'search',placeholder:'Buscar valores…','aria-label':'Buscar valores de la columna'});
  const list=el('div',{class:'eva3-column-values'});
  const status=el('span',{class:'eva3-column-value-count',role:'status'});
  const numeric=type==='number', date=type==='date';
  const options=[['','Ninguna'],...extraConditions,['empty','Está vacío'],['notempty','No está vacío'],...(numeric||date?[['eq',date?'Fecha exacta':'Es igual a'],['gt',date?'Después de':'Mayor que'],['gte',date?'En o después de':'Mayor o igual que'],['lt',date?'Antes de':'Menor que'],['lte',date?'En o antes de':'Menor o igual que'],['between','Está entre']]:[['contains','El texto contiene'],['notcontains','El texto no contiene'],['textis','El texto es exactamente'],['textnot','El texto es distinto de']])];
  const condition=el('select',{'aria-label':'Condición'},...options.map(([value,text])=>el('option',{value,text})));condition.value=filter?.condition||'';
  const first=el('input',{type:numeric?'number':date?'date':'text',step:numeric?'any':null,'aria-label':'Valor de la condición',value:filter?.first||''});
  const second=el('input',{type:numeric?'number':date?'date':'text',step:numeric?'any':null,'aria-label':'Segundo valor de la condición',value:filter?.second||''});
  const color=el('select',{'aria-label':'Filtrar por color'},el('option',{value:'',text:'Todos los colores'}),...colors.map(item=>el('option',{value:item.key,text:item.label})));color.value=filter?.color||'';
  function conditionFields(){first.hidden=!condition.value||['empty','notempty',...extraConditions.map(([value])=>value)].includes(condition.value);second.hidden=condition.value!=='between';}
  condition.addEventListener('change',conditionFields);conditionFields();
  const sortLabels=numeric?['Ordenar de menor a mayor','Ordenar de mayor a menor']:date?['Ordenar de más antiguo a más reciente','Ordenar de más reciente a más antiguo']:['Ordenar A a la Z','Ordenar Z a la A'];
  let menu;
  const close=()=>{menu.hidePopover();trigger.focus({preventScroll:true});};
  const sort=(direction,colorKey=null)=>{onSort(direction,colorKey);close();};
  menu=el('div',{class:'eva3-column-menu',popover:'auto',role:'dialog','aria-label':`Opciones de ${label}`},
    el('div',{class:'eva3-column-menu-title',text:label}),
    ...sortLabels.map((text,index)=>el('button',{type:'button',class:'eva3-column-command',text,onclick:()=>sort(index===0?1:-1)})),
    ...(colors.some(item=>item.key!=='none')?[el('details',{class:'eva3-column-section'},el('summary',{text:'Ordenar por color'}),el('div',{},...colors.map(item=>el('button',{type:'button',class:'eva3-column-command',text:item.label,onclick:()=>sort(1,item.key)})))),el('details',{class:'eva3-column-section',open:Boolean(filter?.color)},el('summary',{text:'Filtrar por color'}),color)]:[]),
    el('details',{class:'eva3-column-section',open:Boolean(filter?.condition)},el('summary',{text:'Filtrar por condición'}),el('div',{class:'eva3-column-condition'},condition,first,second)),
    el('div',{class:'eva3-column-section'},el('div',{class:'eva3-column-values-heading',text:'Filtrar por valores'}),el('div',{class:'eva3-column-select-actions'},el('button',{type:'button',text:'Seleccionar todo',onclick:()=>{visibleValues().forEach(value=>selection.add(value));drawValues();}}),el('button',{type:'button',text:'Borrar',onclick:()=>{visibleValues().forEach(value=>selection.delete(value));drawValues();}}),status),search,list),
    el('button',{type:'button',class:'eva3-column-reset',text:'Quitar filtro de esta columna',onclick:()=>{selection=new Set(values);condition.value='';first.value='';second.value='';color.value='';search.value='';conditionFields();drawValues();}}),
    el('div',{class:'eva3-column-menu-footer'},el('button',{type:'button',text:'Cancelar',onclick:close}),el('button',{type:'button',class:'eva3-column-accept',text:'Aceptar',onclick:()=>{
      const active=selection.size!==values.length||values.some(value=>!selection.has(value));
      onApply({values:active?new Set(selection):null,color:color.value,condition:condition.value,first:first.value,second:second.value});close();
    }})));
  function visibleValues(){return values.filter(value=>normalize(value).includes(normalize(search.value)));}
  function drawValues(){const visible=visibleValues();status.textContent=`${selection.size} de ${values.length}`;list.replaceChildren(...visible.slice(0,200).map(value=>{const input=el('input',{type:'checkbox','aria-label':value||'(Vacío)'});input.checked=selection.has(value);input.addEventListener('change',()=>{if(input.checked)selection.add(value);else selection.delete(value);status.textContent=`${selection.size} de ${values.length}`;});return el('label',{},input,el('span',{text:value||'(Vacío)'}));}),...(visible.length>200?[el('small',{text:'Mostrando 200. Busca para encontrar otros valores.'})]:[]));}
  search.addEventListener('input',drawValues);
  menu.addEventListener('toggle',()=>trigger.setAttribute('aria-expanded',String(menu.matches(':popover-open'))));
  host.append(menu);drawValues();menu.showPopover();
  const box=trigger.getBoundingClientRect(),width=menu.getBoundingClientRect().width,height=menu.getBoundingClientRect().height;
  menu.style.left=`${Math.max(8,Math.min(box.left,innerWidth-width-8))}px`;
  const top=Math.max(8,Math.min(box.bottom+6,innerHeight-height-8));
  menu.style.top=`${top}px`;
  menu.style.maxHeight=`${innerHeight-top-8}px`;
  menu.querySelector('button').focus({preventScroll:true});
}
