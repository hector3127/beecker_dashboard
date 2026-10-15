const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const source=require('node:fs').readFileSync(require('node:path').join(__dirname,'../../apps/portal/static/portal/js/executive_agreements.js'),'utf8');
function harness(failed=false){
 function element(){return {children:[],dataset:{},value:'',hidden:false,textContent:'',listeners:{},append(e){this.children.push(e);},replaceChildren(...list){this.children=list;},addEventListener(type,fn){this.listeners[type]=fn;},focus(){this.focused=true;}};}
 const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);};
 const fields=new Map();node('agreement-form').elements={namedItem:key=>{if(!fields.has(key))fields.set(key,{value:'',focus(){}});return fields.get(key);}};
 node('agreement-form').reset=()=>{for(const field of fields.values())field.value='';};
 const decision=element(),button=element();decision.textContent='Proyecto crítico Ana presupuesto';
 button.dataset={decisionTitle:'Proyecto crítico',decisionOwner:'Ana',decisionAction:'Revisar presupuesto'};
 decision.querySelector=()=>button;node('agreement-rows').querySelectorAll=()=>[decision];
 node('executive-agreements').dataset.endpoint='/ejecutiva/acuerdos/';
 const items=[{id:1,title:'Acuerdo global',owner:'Luis',kind:'agreement',status:'progress',notes:'Revisar',due_date:''}];
 vm.runInNewContext(source,{document:{getElementById:node,createElement:element},fetch:async()=>({ok:!failed,json:async()=>({items})}),FormData:class{}});
 return {node,decision,button,fields};
}
test('decisions remain together with global agreements, filters and prefilled follow-up',async()=>{
 const h=harness();await new Promise(setImmediate);
 assert.equal(h.node('agreement-rows').children.length,2);
 const row=h.node('agreement-rows').children[1];
 assert.equal(row.children.length,8);
 assert.equal(row.children[0].dataset.label,'Proyecto / cuenta o asunto');
 h.button.listeners.click();assert.equal(h.fields.get('title').value,'Proyecto crítico');
 assert.equal(h.fields.get('owner').value,'Ana');assert.equal(h.fields.get('notes').value,'Revisar presupuesto');
 h.node('agreement-filter').value='progress';h.node('agreement-filter').listeners.change();
 assert.equal(h.decision.hidden,true);
 h.node('agreement-filter').value='';h.node('agreement-search').value='critico';h.node('agreement-search').listeners.input();
 assert.equal(h.decision.hidden,false);assert.equal(h.node('agreement-rows').children.length,1);
});
test('failed agreement requests preserve project decisions and expose a retry message',async()=>{
 const h=harness(true);await new Promise(setImmediate);
 assert.equal(h.node('agreement-rows').children[0],h.decision);
 assert.match(h.node('agreement-rows').children.at(-1).children[0].textContent,/Se conservan las decisiones/);
});
