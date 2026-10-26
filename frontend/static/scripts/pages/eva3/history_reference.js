// Controles del histórico AER/T&M. Conserva filas, consultas y reintentos.
import { el } from '#app/lib/dom.js';
import { findAccountLogo, loadAccountLogos } from '#app/lib/account-logos.js';
import { columnColor, matchesColumn, openColumnMenu } from './column_menu.js';
const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
const dateValue = text => {const m = text.trim().match(/^(\d{2})\/(\d{2})\/(\d{2}|\d{4})$/); return m ? `${m[3].length === 2 ? '20' : ''}${m[3]}-${m[2]}-${m[1]}` : '';};
const csvCell = value => {let text = String(value ?? ''); if (/^[=+@-]/.test(text)) text = "'" + text; return '"' + text.replaceAll('"', '""') + '"';};
const status = value => ['completed','completado','finalizado'].includes(normalize(value)) ? 'Finalizado' : ['cancelled','canceled','cancelado'].includes(normalize(value)) ? 'Cancelado' : (value || 'Sin dato');
const text = cell => {const clone = cell.cloneNode(true); clone.querySelectorAll('button,[aria-hidden="true"]').forEach(button => button.remove()); return clone.textContent.trim();};
export function mountHistoryReference(body) {
  const table = body.querySelector('table'); if (!table || body.querySelector('.eva3-history-footer')) return;
  table.id = 'eva3-history-table'; table.classList.add('eva3-history-table');
  const rows = [...table.querySelectorAll('tbody tr[data-closed-id]')];
  const records = rows.map(row => ({row, manager: text(row.cells[0]), id: row.dataset.closedId, service: text(row.cells[2]), name: text(row.cells[3]), status: status(text(row.cells[4])), start: dateValue(text(row.cells[5])), finish: dateValue(text(row.cells[6])), client: row.dataset.closedClient || ''}));
  table.tHead.rows[0].cells[0].after(el('th',{scope:'col',text:'Cuenta'}));
  const logos=loadAccountLogos();
  records.forEach(record=>{
    const initials=record.client.trim().split(/\s+/).filter(Boolean).slice(0,2).map(word=>word[0]).join('').toUpperCase()||'—';
    const host=el('span',{class:'eva3-account-logo','aria-hidden':'true',text:initials});
    record.row.cells[0].after(el('td',{},el('span',{class:'eva3-account'},host,el('span',{text:record.client||'Sin cuenta'}))));
    logos.then(items=>{const logo=findAccountLogo(items,record.client);if(!logo)return;const image=el('img',{src:logo.url,alt:'',loading:'lazy',decoding:'async'});image.addEventListener('error',()=>host.replaceChildren(initials),{once:true});host.replaceChildren(image);});
  });
  const clear = el('button', {id: 'eva3-history-clear', type: 'button', text: 'Limpiar filtros', class: 'eva3-history-clear'});
  const filters = new Map();
  const count = el('span', {id: 'eva3-history-count', role: 'status', 'aria-live': 'polite'});
  const pages = el('nav', {class: 'eva3-history-pages', 'aria-label': 'Páginas del histórico'});
  const sizeSelect = el('select', {id: 'eva3-history-size', 'aria-label': 'Proyectos históricos por página'}, ...[12,25,50,100].map(size => el('option', {value: size, text: `${size} / página`})));
  body.append(el('div', {class: 'eva3-history-footer'}, count, clear, pages, sizeSelect));
  let page = 1, size = 12, sortIndex = null, direction = 1, sortColor = null;
  function numeric(cell) {const value = text(cell).replace(/[,\s%]/g, ''); return /^-?\d+(\.\d+)?$/.test(value) ? Number(value) : null;}
  function value(record, index) {return index >= 8 ? numeric(record.row.cells[index]) : index === 6 ? record.start || null : index === 7 ? record.finish || null : index === 5 ? record.status : text(record.row.cells[index]);}
  function filtered() {
    const result = records.filter(record => [...filters].every(([index,filter])=>matchesColumn(text(record.row.cells[index]),value(record,index),columnColor(record.row.cells[index]).key,filter)));
    if (sortIndex !== null) result.sort((a,b) => {
      if(sortColor){const order=Number(columnColor(b.row.cells[sortIndex]).key===sortColor)-Number(columnColor(a.row.cells[sortIndex]).key===sortColor);if(order)return order;}
      const av=value(a,sortIndex),bv=value(b,sortIndex);if(av===null)return bv===null?0:1;if(bv===null)return -1;return direction*(typeof av==='number'?av-bv:String(av).localeCompare(String(bv),'es',{numeric:true}));
    });
    return result;
  }
  const empty = el('tr', {class: 'eva3-history-empty'}, el('td', {colspan: 12, text: 'Sin proyectos que coincidan con los filtros.'}));
  function render() {
    const result = filtered(), totalPages = Math.max(1, Math.ceil(result.length / size)); page = Math.min(page,totalPages);
    const shown = new Set(result.slice((page-1)*size,page*size).map(record => record.row));
    // Reuse actual nodes so asynchronous consumption and retry handlers stay attached.
    table.tBodies[0].replaceChildren(...result.map(record => record.row), ...records.filter(record=>!result.includes(record)).map(record=>record.row));
    records.forEach(record => {record.row.hidden = !shown.has(record.row);});
    if (!result.length) table.tBodies[0].append(empty);
    count.textContent = `Mostrando ${shown.size} de ${result.length} proyectos`;
    table.querySelectorAll('thead th').forEach((th,index) => {th.setAttribute('aria-sort',sortIndex===index?(direction===1?'ascending':'descending'):'none');th.classList.toggle('eva3-column-filtered',filters.has(index));th.querySelector('button').setAttribute('aria-label',`Opciones de ${th.dataset.label}${filters.has(index)?', filtro aplicado':''}`);});
    const numbers=Array.from({length:totalPages},(_,index)=>index+1).filter(number=>number===1||number===totalPages||Math.abs(number-page)<=1);
    const buttons=[];
    numbers.forEach((number,index)=>{if(index&&number-numbers[index-1]>1)buttons.push(el('span',{text:'…'}));buttons.push(el('button',{type:'button','aria-label':`Histórico página ${number}`,'aria-current':number===page?'page':null,text:number,onclick:()=>{page=number;render();}}));});
    pages.replaceChildren(el('button',{type:'button',text:'‹','aria-label':'Histórico página anterior',disabled:page===1,onclick:()=>{page--;render();}}),...buttons,el('button',{type:'button',text:'›','aria-label':'Histórico página siguiente',disabled:page===totalPages,onclick:()=>{page++;render();}}));
  }
  records.forEach(record => {
    record.row.cells[3].replaceChildren(el('span',{class:`eva3-service service-${record.service==='AER'?'aer':'tym'}`,text:record.service}));
    record.row.cells[5].replaceChildren(el('span',{class:`eva3-history-status ${record.status==='Finalizado'?'finished':record.status==='Cancelado'?'cancelled':'unknown'}`,text:record.status}));
  });
  table.querySelectorAll('thead th').forEach((th,index)=>{
    const label=th.textContent;th.dataset.label=label;th.setAttribute('scope','col');
    const trigger=el('button',{type:'button','aria-expanded':'false','aria-haspopup':'dialog',onclick:()=>openColumnMenu({host:body,trigger,label,type:index>=8?'number':index===6||index===7?'date':'text',entries:records.map(record=>({raw:text(record.row.cells[index]),color:columnColor(record.row.cells[index])})),filter:filters.get(index),onApply:filter=>{if(filter.values||filter.color||filter.condition)filters.set(index,filter);else filters.delete(index);page=1;render();},onSort:(order,color)=>{sortIndex=index;direction=order;sortColor=color;page=1;render();}})},el('span',{text:label}),el('span',{'aria-hidden':'true',class:'eva3-column-chevron',text:' ▾'}));
    th.replaceChildren(trigger);
  });
  sizeSelect.addEventListener('change',()=>{size=Number(sizeSelect.value);page=1;render();});
  clear.addEventListener('click',()=>{filters.clear();page=1;render();});
  body.addEventListener('eva3-history-updated',render);
  const summary=body.closest('details').querySelector('summary');
  const exportButton=el('button',{id:'eva3-history-export',class:'eva3-export',type:'button',text:'↓ Exportar',title:'Descargar todos los proyectos históricos filtrados',onclick:event=>{
    event.preventDefault();event.stopPropagation();
    const content=[[...table.tHead.rows[0].cells].map(th=>th.dataset.label),...filtered().map(record=>[...record.row.cells].map(text))].map(row=>row.map(csvCell).join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob(['\uFEFF'+content],{type:'text/csv;charset=utf-8'}));el('a',{href:url,download:'EVA3-historico-AER-TYM.csv'}).click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }});
  summary.querySelector('#eva3-history-export')?.remove();summary.append(exportButton);
  render();
}
