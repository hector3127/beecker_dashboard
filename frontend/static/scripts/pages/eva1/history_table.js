import { mountAccountColumn } from "./account_column.js";
// Histórico IXB/RaaS/SaaS: diez filas por página y CSV de todo el resultado.
import { el } from '#app/lib/dom.js';
import { mountTableColumns, cellText } from '../eva/table_columns.js';

const csvCell=value=>{let text=String(value??'');if(/^[=+@-]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
export function mountIxbHistory(body){
  const table=body.querySelector('table');if(!table)return;
  const rows=[...table.querySelectorAll('tbody tr[data-manager]')];
  mountAccountColumn(table,rows);
  let page=1,size=10,columns;
  const footer=body.querySelector('.table-bottom');
  const count=el('span',{id:'eva-history-count',role:'status','aria-live':'polite'});
  const pages=el('nav',{class:'eva-history-pages','aria-label':'Páginas del histórico IXB'});
  const bottom=footer||el('div',{class:'table-bottom'});
  bottom.classList.add('eva-history-footer');
  const sizes=el('select',{class:'eva-history-size',id:'eva-history-size','aria-label':'Proyectos por página del histórico IXB'},...[10,25,50,100].map(value=>el('option',{value,text:value})));
  bottom.replaceChildren(count,pages,sizes);if(!footer)body.append(bottom);
  const results=()=>columns.sort(rows.filter(columns.matches));
  const empty=el('tr',{class:'eva-history-empty'},el('td',{colspan:26,class:'vacio',text:'No hay proyectos que coincidan con los filtros.'}));
  function render(){
    const filtered=results(),totalPages=Math.max(1,Math.ceil(filtered.length/size));page=Math.min(page,totalPages);
    const shown=new Set(filtered.slice((page-1)*size,page*size));
    const matched=new Set(filtered);
    table.tBodies[0].replaceChildren(...filtered,...rows.filter(row=>!matched.has(row)));
    rows.forEach(row=>{row.hidden=!shown.has(row);});
    if(!filtered.length)table.tBodies[0].append(empty);
    count.textContent=`Mostrando ${filtered.length?(page-1)*size+1:0}–${Math.min(page*size,filtered.length)} de ${filtered.length} proyectos`;
    const move=next=>{page=next;render();};
    pages.replaceChildren(el('button',{type:'button','aria-label':'Histórico IXB página anterior',text:'‹',disabled:page===1,onclick:()=>move(page-1)}),el('span',{class:'eva-history-current','aria-current':'page',text:`${page} / ${totalPages}`}),el('button',{type:'button','aria-label':'Histórico IXB página siguiente',text:'›',disabled:page===totalPages,onclick:()=>move(page+1)}));
  }
  columns=mountTableColumns({table,rows,types:Object.fromEntries(Array.from({length:26},(_,index)=>[index,[6,7].includes(index)?'date':index>=8?'number':'text'])),onChange:()=>{page=1;render();}});
  const summary=body.closest('details').querySelector('summary');
  summary.append(el('button',{id:'eva-history-export',type:'button',class:'eva-btn eva-history-export',text:'↓ Exportar',title:'Exportar todos los proyectos históricos filtrados',onclick:event=>{
    event.preventDefault();event.stopPropagation();
    const headers=[...table.tHead.querySelectorAll('th[data-column-index]')].sort((a,b)=>Number(a.dataset.columnIndex)-Number(b.dataset.columnIndex)).map(th=>th.dataset.columnLabel);
    const content=[headers,...results().map(row=>[...row.cells].map(cellText))].map(row=>row.map(csvCell).join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob(['\uFEFF'+content],{type:'text/csv;charset=utf-8'}));el('a',{href:url,download:'EVA1-historico-IXB-RaaS-SaaS.csv'}).click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }}));
  sizes.addEventListener('change',()=>{size=Number(sizes.value);page=1;render();});
  render();
}
