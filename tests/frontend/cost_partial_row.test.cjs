const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

test('loading a partial breakdown updates hours, cost, margin, state and global summary',async()=>{
 const html=fs.readFileSync(path.join(__dirname,'../../apps/portal/templates/portal/costos_detalle.html'),'utf8');
 const source=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n')
 .replace('{% url "portal:proyecto_detalle" "project-placeholder" %}', '/proyectos/project-placeholder/');
 const nodes=new Map();
 const node=id=>{if(!nodes.has(id))nodes.set(id,{value:id==='cost-filter'?'all':'',textContent:'',innerHTML:'',style:{},dataset:{},addEventListener(){}});return nodes.get(id);};
 let calculated=false;
 const partial={id:'AER.MCC.005',hours:100,cost:700,revenue:10000,margin:93,complete:false,missing_hours:7,people:[{name:'Ana',hours:93,rate:7,band:'A2',cost:651}],scope_start:'2026-01-01',scope_end:'2026-10-15'};
 const summary=()=>({projects:[calculated?partial:{id:partial.id,cost:null,hours:null,revenue:10000,complete:false,error:'Consulta anterior fallida'}],cost:calculated?700:0,complete:false,pending:calculated?0:1,deduplicated_entries:calculated?2:0,band_month:'2026-10'});
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../apps/portal/static/portal/js/executive_numbers.js'),'utf8')+'\n'+source,{URL,URLSearchParams,document:{getElementById:node},window:{location:new URL('http://localhost/ejecutiva/costos/detalle/')},fetch:async url=>({ok:true,json:async()=>{if(url.includes('&id=')){calculated=true;return partial;}return summary();}})});
 await new Promise(resolve=>setImmediate(resolve));
 const cells=Array.from({length:7},()=>({textContent:'Pendiente',innerHTML:'',style:{}}));
 const target={textContent:'',innerHTML:'',dataset:{}};
 const detail={hidden:true,querySelector:()=>target};
 const row={cells,nextElementSibling:detail};
 const button={dataset:{persons:partial.id},closest:()=>row};
 await node('cost-audit-body').onclick({target:{closest:selector=>selector==='[data-persons]'?button:null}});
 assert.equal(cells[1].textContent,'100');
 assert.match(cells[0].innerHTML, /class="cost-project-link"/);
 assert.match(cells[2].textContent,/700/);
 assert.equal(cells[4].textContent,'93%*');
 assert.match(cells[5].innerHTML,/Costo parcial/);
 assert.match(cells[5].innerHTML,/7 h pendientes/);
 assert.match(node('cost-total').textContent,/700/);
 assert.equal(node('cost-pending').textContent,0);
 assert.equal(detail.hidden,false);
});
