// @ts-check
// Filtros, paginación y presentación sobre las cifras originales del servidor.
import { formatMoney, plain } from '#app/lib/format.js';
import { el, svg } from '#app/lib/dom.js';
import { icon } from '#app/ui/icons.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { watchLoadingMessages } from '#app/ui/portal-loading.js';
watchLoadingMessages();
const byId = id => document.getElementById(id);
const rows = [...document.querySelectorAll('tr[data-name]')];
const originalOrder = new Map(rows.map((row,index)=>[row,index]));
const search = byId('account-search');
const filter = byId('account-filter');
const state = byId('account-state');
const body = byId('accounts-body');
const empty = byId('accounts-empty');
let page = 1, size = 15, sortIndex = -1, ascending = true;

for (const [index,row] of rows.entries()) {
  const name = row.dataset.name;
  const initials = name.trim().split(/\s+/).slice(0,2).map(word=>word[0]).join('').toUpperCase();
  row.cells[0].querySelector('a').prepend(el('span',{class:`account-avatar avatar-${index%5}`,'aria-hidden':'true',text:initials}));
  const accountLink=row.cells[0].querySelector('a'),costLink=row.querySelector('.detail-link');
  const menu=el('details',{class:'account-row-menu'},
    el('summary',{'aria-label':`Acciones de ${name}`,title:`Acciones de ${name}`,text:'⋮'}),
    el('div',{class:'account-row-menu-links'},
      el('a',{href:accountLink.getAttribute('href'),text:'Abrir cuenta'}),
      el('a',{href:costLink.getAttribute('href'),text:'Ver detalle de costos'})
    )
  );
  menu.addEventListener('toggle',()=>{
    if(menu.open)menu.classList.toggle('opens-below',menu.getBoundingClientRect().top-row.closest('.accounts-scroll').getBoundingClientRect().top<110);
  });
  row.cells[7].append(menu);
  for (const link of row.querySelectorAll('a')) link.dataset.baseHref = link.getAttribute('href');
}
for (const span of document.querySelectorAll('[data-summary-icon]')) {
  const name = span.dataset.summaryIcon;
  span.append(name === 'clock' ? svg('svg',{viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.8','aria-hidden':'true'},svg('circle',{cx:12,cy:12,r:10}),svg('path',{d:'M12 6v6l5 3'})) : icon(name));
}
for (const cell of document.querySelectorAll('[data-money]')) {
  const partial = cell.closest('tr').dataset.partial === 'true' && cell.cellIndex !== 2;
  cell.textContent = formatMoney(Number(cell.dataset.money)) + (partial ? '*' : '');
}
const healthy = rows.filter(row=>row.dataset.classification === 'healthy').length;
const pending = rows.filter(row=>row.dataset.classification === 'pending').length;
byId('summary-healthy').textContent = String(healthy);
byId('summary-pending').textContent = String(pending);
for (const [key,value] of [['healthy',healthy],['pending',pending]]) {
  const pct = rows.length ? value/rows.length*100 : 0;
  byId(`summary-${key}-percent`).textContent = `${pct.toFixed(1)}% del total`;
  byId(`summary-${key}-progress`).value = pct;
}
const complete = rows.filter(row=>!['pending','future'].includes(row.dataset.classification) && row.dataset.margin !== '');
byId('summary-margin').textContent = complete.length ? `${(complete.reduce((sum,row)=>sum+Number(row.dataset.margin),0)/complete.length).toLocaleString('es-MX',{maximumFractionDigits:1})}%` : '—';
byId('summary-margin').classList.toggle('is-negative', complete.length>0 && complete.reduce((sum,row)=>sum+Number(row.dataset.margin),0)<0);
document.addEventListener('click',event=>{for(const menu of document.querySelectorAll('.account-row-menu[open]'))if(!menu.contains(event.target))menu.open=false;});
document.addEventListener('keydown',event=>{if(event.key==='Escape')for(const menu of document.querySelectorAll('.account-row-menu[open]')){menu.open=false;menu.querySelector('summary').focus();}});
const headers = [...document.querySelectorAll('.accounts-scroll thead th button')];
function restore() {
  const params=readParams();
  search.value=params.get('buscar')||'';
  filter.value=['healthy','intermediate','unhealthy','future','pending'].includes(params.get('clasificacion')) ? params.get('clasificacion') : '';
  state.value=['complete','partial','pending','future'].includes(params.get('estado')) ? params.get('estado') : '';
  page=Math.max(1,parseInt(params.get('pagina')||'1',10)||1);
  size=[15,25,50,100].includes(Number(params.get('tamano'))) ? Number(params.get('tamano')) : 15;
  byId('accounts-page-size').value=String(size);
  sortIndex=/^[0-6]$/.test(params.get('orden')||'') ? Number(params.get('orden')) : -1;
  ascending=params.get('sentido')!=='desc';
}
function draw() {
  const wanted=plain(search.value).trim();
  const matches=rows.filter(row=>{
    const classification=row.dataset.classification, partial=row.dataset.partial==='true';
    return plain(`${row.dataset.name} ${row.cells[6].textContent}`).includes(wanted) &&
      (!filter.value || classification===filter.value) && (!state.value ||
      state.value==='complete' && !partial && !['pending','future'].includes(classification) ||
      state.value==='partial' && partial || state.value==='pending' && classification==='pending' ||
      state.value==='future' && classification==='future');
  });
  const value=row=>sortIndex===0 ? row.dataset.name : sortIndex>=2 && sortIndex<=4 ? Number(row.cells[sortIndex].dataset.money) : sortIndex===5 ? row.dataset.margin==='' ? null : Number(row.dataset.margin) : sortIndex===1 ? Number(row.cells[1].textContent) : row.cells[sortIndex].textContent.trim();
  rows.sort((a,b)=>{
    if(sortIndex<0)return originalOrder.get(a)-originalOrder.get(b);
    const av=value(a),bv=value(b);
    if(av===null&&bv===null)return 0;if(av===null)return 1;if(bv===null)return -1;
    return (typeof av==='number' ? av-bv : String(av).localeCompare(String(bv),'es',{sensitivity:'base'}))*(ascending?1:-1);
  });
  const filtered=rows.filter(row=>matches.includes(row));
  const pages=Math.max(1,Math.ceil(filtered.length/size));page=Math.min(page,pages);
  writeParams({buscar:search.value.trim(),clasificacion:filter.value,estado:state.value,pagina:page>1?page:'',tamano:size!==15?size:'',orden:sortIndex>=0?sortIndex:'',sentido:sortIndex>=0?ascending?'asc':'desc':''});
  const visible=new Set(filtered.slice((page-1)*size,page*size));
  for(const row of rows){row.hidden=!visible.has(row);body.insertBefore(row,empty);
    for(const link of row.querySelectorAll('a')){const url=new URL(link.dataset.baseHref,location.href);url.searchParams.set('volver',location.pathname+location.search);link.setAttribute('href',url.pathname+url.search);}
  }
  byId('account-count').textContent=`${filtered.length} de ${rows.length} cuentas`;
  empty.hidden=filtered.length!==0;
  byId('accounts-page-label').textContent=`Mostrando ${filtered.length?(page-1)*size+1:0}–${Math.min(page*size,filtered.length)} de ${filtered.length} cuentas`;
  byId('accounts-prev').disabled=page===1;byId('accounts-next').disabled=page>=pages;
  const numbers=[...new Set([1,pages,...Array.from({length:5},(_,i)=>page+i-2).filter(n=>n>=1&&n<=pages)])].sort((a,b)=>a-b);
  const buttons=[];numbers.forEach((n,i)=>{if(i&&n>numbers[i-1]+1)buttons.push(el('span',{text:'…'}));buttons.push(el('button',{type:'button','aria-label':`Página ${n}`,'aria-current':n===page?'page':null,text:String(n),onclick:()=>{page=n;draw();}}));});
  byId('accounts-pages').replaceChildren(...buttons);
  headers.forEach((button,index)=>button.closest('th').setAttribute('aria-sort',index===sortIndex?ascending?'ascending':'descending':'none'));
}
headers.forEach((button,index)=>button.addEventListener('click',()=>{ascending=sortIndex===index?!ascending:true;sortIndex=index;page=1;draw();}));
search.addEventListener('input',()=>{page=1;draw();});filter.addEventListener('change',()=>{page=1;draw();});state.addEventListener('change',()=>{page=1;draw();});
byId('account-clear').addEventListener('click',()=>{search.value='';filter.value='';state.value='';sortIndex=-1;page=1;draw();search.focus();});
byId('accounts-page-size').addEventListener('change',event=>{size=Number(event.target.value);page=1;draw();});
byId('accounts-prev').addEventListener('click',()=>{page-=1;draw();});byId('accounts-next').addEventListener('click',()=>{page+=1;draw();});
addEventListener('popstate',()=>{restore();draw();});restore();draw();
