const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

test('prepared sprint breakdown expands locally with people, without repeating revenue',async()=>{
 const template=fs.readFileSync(path.join(__dirname,'../../apps/portal/templates/portal/costos_detalle.html'),'utf8');
 const source=template.split('{% block scripts %}<script>')[1].split('</script>')[0]
  .replace('{% url "portal:proyecto_detalle" "project-placeholder" %}','/proyectos/project-placeholder/');
 const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{value:id==='cost-filter'?'all':'',style:{},dataset:{},addEventListener(){}});return nodes.get(id);};
 const person={name:'Ana <Test>',hours:2,band:'A2',band_month:'Octubre',rate:7,cost:14};
 const detail={id:'P1',hours:2,cost:14,revenue:100,margin:86,complete:true,people:[person],task_details_complete:true,
 sprints:[{label:'S1',project_id:'P1_S1',hours:2,cost:14,complete:true,people:[person]}]};
 let requests=0;
 vm.runInNewContext(source,{URL,URLSearchParams,document:{getElementById:node},window:{location:new URL('http://localhost/ejecutiva/costos/detalle/')},fetch:async()=>{requests++;return {ok:true,json:async()=>({projects:[detail],prepared_details:{p1:detail},cost:14,pending:0,deduplicated_entries:1,band_month:'2026-10'})};}});
 await new Promise(setImmediate);
 const target={dataset:{},innerHTML:''};const expanded={hidden:true,querySelector:()=>target};
 const cells=Array.from({length:7},()=>({style:{}}));const row={cells,nextElementSibling:expanded};
 const button={dataset:{persons:'P1'},closest:()=>row};
 await node('cost-audit-body').onclick({target:{closest:s=>s==='[data-persons]'?button:null}});
 assert.equal(requests,1);
 assert.equal(expanded.hidden,false);
 assert.match(target.innerHTML,/Consumo por sprint/);
 assert.match(target.innerHTML,/P1_S1/);
 assert.match(target.innerHTML,/Personas y esfuerzo/);
 assert.match(target.innerHTML,/Ana &lt;Test&gt;/);
 assert.match(target.innerHTML,/no se suma ni se reparte/);
 assert.doesNotMatch(target.innerHTML,/Ana <Test>/);
});
