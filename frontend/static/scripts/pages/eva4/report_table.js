// Presentación común de EVA 4: menús, exportación completa y páginas.
import { el, svg } from '#app/lib/dom.js';
import { mountTableColumns, cellText } from '../eva/table_columns.js';
import { findAccountLogo } from '../account/logo-lookup.js';
let logos;
export function icon(name){const paths={gear:'m9 2-.5 3-2 1-2.8-1L1.5 9l2.5 2v2l-2.5 2 2.2 3.7L6.5 18l2 1 .5 3h5l.5-3 2-1 2.8.7 2.2-3.7-2.5-2v-2l2.5-2-2.2-3.7-2.8 1-2-1L14 2ZM16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',layers:'m3 7 9-4 9 4-9 4zM3 12l9 4 9-4M3 17l9 4 9-4',play:'m10 8 6 4-6 4zM21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',pause:'M9 8v8M15 8v8M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',renew:'M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5M4 16a8 8 0 0 0 14 3l3-3m0 5v-5h-5',clients:'M4 21V4h10v17M14 9h6v12M7 7h4M7 11h4M7 15h4M7 19h4M17 12v2M17 17v2',database:'M4 5c0-4 16-4 16 0s-16 4-16 0v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0'};return el('span',{class:`eva4-reference-icon icon-${name}`},svg('svg',{viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':1.8,'stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true'},svg('path',{d:paths[name]||paths.layers})));}
export function countryCell(cell){
  const name=cell.textContent.trim(),code={MEX:'MX',MX:'MX',USA:'US',US:'US',GTM:'GT',GT:'GT',COL:'CO',CO:'CO',ECU:'EC',EC:'EC',CHL:'CL',CL:'CL',BRA:'BR',BR:'BR'}[name];if(!code)return;
  const flag=svg('svg',{viewBox:'0 0 24 16',width:21,height:14,class:'eva4-country-flag','aria-hidden':'true'}),rect=(x,y,width,height,fill)=>svg('rect',{x,y,width,height,fill});
  if(code==='MX'||code==='GT'){flag.append(rect(0,0,8,16,code==='MX'?'#098050':'#51b6df'),rect(8,0,8,16,'#fff'),rect(16,0,8,16,code==='MX'?'#d82f37':'#51b6df'),svg('circle',{cx:12,cy:8,r:1.4,fill:'#b59642'}));}
  if(code==='CO'||code==='EC')flag.append(rect(0,0,24,8,'#f7d435'),rect(0,8,24,4,'#2547a2'),rect(0,12,24,4,'#cf3341'));
  if(code==='CL')flag.append(rect(0,0,24,8,'#fff'),rect(0,8,24,8,'#da3441'),rect(0,0,8,8,'#234c9c'),svg('path',{d:'m4 1 1 2h2L5 4l1 2-2-1-2 1 1-2-2-1h2z',fill:'#fff'}));
  if(code==='BR')flag.append(rect(0,0,24,16,'#19904c'),svg('path',{d:'M12 1 23 8 12 15 1 8Z',fill:'#f7d63b'}),svg('circle',{cx:12,cy:8,r:4,fill:'#2458a4'}));
  if(code==='US'){flag.append(rect(0,0,24,16,'#fff'),...Array.from({length:7},(_,i)=>rect(0,i*16/6.5,24,16/13,'#c83d4b')),rect(0,0,10,9,'#29487d'),...Array.from({length:9},(_,i)=>svg('circle',{cx:2+(i%3)*3,cy:2+Math.floor(i/3)*2.5,r:.45,fill:'#fff'})));}
  cell.replaceChildren(flag,' ',name);
}
export function clientCell(cell){const name=cell.textContent.trim(),initials=name.split(/\s+/).slice(0,2).map(word=>word[0]).join('');const host=el('span',{class:'eva4-client-logo','aria-hidden':'true',text:initials});cell.replaceChildren(el('span',{class:'eva4-client-name'},host,el('span',{text:name})));if(!logos)logos=fetch('/api/v1/account-logos/',{credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(body=>body?.data?.items||[]).catch(()=>[]);logos.then(items=>{const logo=findAccountLogo(items,name);if(!logo)return;const img=el('img',{src:logo.url,alt:'',loading:'lazy',decoding:'async'});img.addEventListener('error',()=>host.replaceChildren(initials),{once:true});host.replaceChildren(img);});}
const csvCell=value=>{let text=String(value??'');if(/^[=+@-]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
export function mountReportTable({table,rows,types,kind,onCount=()=>{},totals=null}){
  const section=table.closest('section'),heading=section.querySelector('h2'),note=section.querySelector('.eva4-note');
  const header=el('div',{class:'eva4-section-heading'},icon(kind==='clients'?'clients':kind==='renewals'?'renew':'database'),el('div',{},heading,...(note?[note]:[])));
  section.prepend(header);
  let page=1,size=10,columns,wanted='';
  const count=el('span',{id:`${table.id}-count`,role:'status','aria-live':'polite'}),nav=el('nav',{'aria-label':`Páginas de ${kind}`,class:'eva4-reference-pages'});
  const sizes=el('select',{'aria-label':`Filas por página de ${kind}`},...[10,25,50,100].map(value=>el('option',{value,text:`${value} / página`})));
  const footer=el('div',{class:'eva4-reference-footer'},count,nav,sizes);section.append(footer);
  const normalize=text=>String(text).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const filtered=()=>columns.sort(rows.filter(row=>columns.matches(row)&&normalize(cellText(row)).includes(wanted)));
  const unit=kind==='processes'?'procesos':kind==='clients'?'clientes':'renovaciones';
  function render(){const result=filtered(),totalPages=Math.max(1,Math.ceil(result.length/size));page=Math.min(page,totalPages);const shown=new Set(result.slice((page-1)*size,page*size));const matches=new Set(result);table.tBodies[0].replaceChildren(...result,...rows.filter(row=>!matches.has(row)),...(totals?[totals]:[]));rows.forEach(row=>{row.hidden=!shown.has(row);});if(!result.length&&!totals)table.tBodies[0].append(el('tr',{class:'eva4-no-results'},el('td',{colspan:table.tHead.querySelectorAll('th[scope=col]').length,text:'Sin resultados.'})));count.textContent=`Mostrando ${shown.size} de ${result.length} ${unit}`;const move=next=>{page=next;render();};const numbers=Array.from({length:totalPages},(_,i)=>i+1).filter(n=>n===1||n===totalPages||Math.abs(n-page)<=1);const buttons=[];numbers.forEach((n,i)=>{if(i&&n-numbers[i-1]>1)buttons.push(el('span',{text:'…'}));buttons.push(el('button',{type:'button','aria-label':`${kind} página ${n}`,'aria-current':page===n?'page':null,text:n,onclick:()=>move(n)}));});nav.replaceChildren(el('button',{type:'button','aria-label':`${kind} página anterior`,text:'‹',disabled:page===1,onclick:()=>move(page-1)}),...buttons,el('button',{type:'button','aria-label':`${kind} página siguiente`,text:'›',disabled:page===totalPages,onclick:()=>move(page+1)}));onCount({shown:result.length,total:rows.length});return {shown:result.length,total:rows.length};}
  columns=mountTableColumns({table,rows,types,onChange:()=>{page=1;render();}});
  header.append(el('button',{type:'button',id:`${table.id}-export`,class:'eva4-export',text:'↓ Exportar',title:'Exportar todos los resultados filtrados',onclick:()=>{const heads=[...table.tHead.querySelectorAll('th[data-column-index]')].sort((a,b)=>a.dataset.columnIndex-b.dataset.columnIndex).map(th=>th.dataset.columnLabel);const text=[heads,...filtered().map(row=>[...row.cells].map(cellText))].map(row=>row.map(csvCell).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob(['\uFEFF'+text],{type:'text/csv;charset=utf-8'}));el('a',{href:url,download:`EVA4-${kind}.csv`}).click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}));
  sizes.addEventListener('change',()=>{size=Number(sizes.value);page=1;render();});render();return {filter(text){wanted=normalize(text);page=1;return render();}};
}
