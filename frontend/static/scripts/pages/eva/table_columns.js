// Menús reutilizables para tablas EVA, incluidos encabezados agrupados.
import { el } from '#app/lib/dom.js';
import { columnColor, matchesColumn, openColumnMenu } from '../eva3/column_menu.js';
export function cellText(cell) {
  const clone=cell.cloneNode(true);clone.querySelectorAll('button,[aria-hidden="true"]').forEach(node=>node.remove());return clone.textContent.trim();
}
function leafHeaders(table) {
  const grid=[];
  [...table.tHead.rows].forEach((row,r)=>{grid[r] ||= [];let c=0;[...row.cells].forEach(th=>{while(grid[r][c])c++;for(let y=r;y<r+th.rowSpan;y++){grid[y] ||= [];for(let x=c;x<c+th.colSpan;x++)grid[y][x]=th;}c+=th.colSpan;});});
  return (grid.at(-1)||[]).map((th,index)=>({th,index,group:grid[0][index]})).filter(item=>item.th.colSpan===1);
}
export function mountTableColumns({table,rows,types={},exclude=[],onChange=()=>{},standalone=false,groupLabels=true,conditions={}}) {
  const filters=new Map();let sortIndex=null,direction=1,sortColor=null;
  table.classList.add('eva-columns-table');
  const host=table.closest('section')||table.parentElement;
  const clear=el('button',{type:'button',class:'eva-column-clear',text:'Limpiar filtros de columnas',hidden:true,onclick:()=>{filters.clear();update();}});
  table.parentElement.before(clear);
  function type(index){return types[index]||'text';}
  function value(row,index){const raw=cellText(row.cells[index]);if(type(index)==='number'){const cleaned=raw.replace(/[,\s%]/g,'');return /^-?\d+(\.\d+)?$/.test(cleaned)?Number(cleaned):null;}if(type(index)==='date'){const match=raw.match(/^(\d{2})\/(\d{2})\/(\d{2}|\d{4})$/);if(match)return `${match[3].length===2?'20':''}${match[3]}-${match[2]}-${match[1]}`;return /^\d{4}-\d{2}-\d{2}$/.test(raw)?raw:null;}return raw;}
  const matches=row=>[...filters].every(([index,filter])=>{
    const custom=conditions[index]?.find(item=>item.value===filter.condition);
    return (!custom||custom.matches(row))&&matchesColumn(cellText(row.cells[index]),value(row,index),columnColor(row.cells[index]).key,custom?{...filter,condition:''}:filter);
  });
  function sort(items){return [...items].sort((a,b)=>{if(sortIndex===null)return 0;if(sortColor){const order=Number(columnColor(b.cells[sortIndex]).key===sortColor)-Number(columnColor(a.cells[sortIndex]).key===sortColor);if(order)return order;}const av=value(a,sortIndex),bv=value(b,sortIndex);if(av===null)return bv===null?0:1;if(bv===null)return -1;return direction*(typeof av==='number'?av-bv:String(av).localeCompare(String(bv),'es',{numeric:true}));});}
  const headers=leafHeaders(table).filter(({index})=>!exclude.includes(index));
  function update(){
    clear.hidden=!filters.size;
    headers.forEach(({th,index})=>{th.classList.toggle('eva3-column-filtered',filters.has(index));th.setAttribute('aria-sort',index===sortIndex?(direction===1?'ascending':'descending'):'none');th.querySelector('button').setAttribute('aria-label',`Opciones de ${th.dataset.columnLabel}${filters.has(index)?', filtro aplicado':''}`);});
    if(standalone){sort(rows).forEach(row=>{row.hidden=!matches(row);table.tBodies[0].append(row);});}
    onChange();
  }
  headers.forEach(({th,index,group})=>{
    const label=(groupLabels&&group!==th?`${cellText(group)} · `:'')+(th.title||th.getAttribute('aria-label')||cellText(th));th.dataset.columnLabel=label;th.dataset.columnIndex=String(index);th.classList.add('eva-column-leaf');
    const content=el('span',{},...th.childNodes);
    const trigger=el('button',{class:'eva-column-trigger',type:'button','aria-expanded':'false','aria-haspopup':'dialog','aria-label':`Opciones de ${label}`,onclick:()=>openColumnMenu({host,trigger,label,type:type(index),extraConditions:(conditions[index]||[]).map(item=>[item.value,item.label]),entries:rows.map(row=>({raw:cellText(row.cells[index]),color:columnColor(row.cells[index])})),filter:filters.get(index),onApply:filter=>{if(filter.values||filter.color||filter.condition)filters.set(index,filter);else filters.delete(index);update();},onSort:(order,color)=>{sortIndex=index;direction=order;sortColor=color;update();}})},content);
    th.replaceChildren(trigger);
  });
  return {matches,sort,refresh:update,clear(){filters.clear();update();}};
}
