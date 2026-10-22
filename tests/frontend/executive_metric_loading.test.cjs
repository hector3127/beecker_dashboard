const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const domState=require('./dom_state.cjs');
const source=fs.readFileSync('apps/portal/static/portal/js/executive_report.js','utf8');

function render(commercial,status){
 const nodes=new Map();
 const node=id=>{if(!nodes.has(id))nodes.set(id,{...domState(),textContent:'',innerHTML:'',dataset:{endpoint:'/ejecutiva/actualizacion/'}});return nodes.get(id);};
 const financial={loaded_at:'2026-10-21T10:00:00',revenue:{invoiced:100,collections_percent:70},costs:{cost:10,complete:true}};
 if(commercial!==undefined)financial.commercial=commercial;
 node('financial-cache').textContent=JSON.stringify(financial);
 node('operations-cache').textContent=JSON.stringify({partial:false,projects:1,etc:100,advance:50,facturability:75,investment_operational:10});
 let requests=0,reloads=0,stopped=0;
 vm.runInNewContext(source,{
  executiveMoney:value=>value==null?'Pendiente':String(value),
  document:{getElementById:node},
  location:{href:'http://localhost/',search:'',reload(){reloads++;}},URL,
  setInterval:()=>1,clearInterval(){stopped++;},
  fetch:async()=>{requests++;return {ok:true,json:async()=>status};}
 });
 return {node,get requests(){return requests;},get reloads(){return reloads;},get stopped(){return stopped;}};
}

test('only absent commercial data displays loading while existing metrics stay visible',async()=>{
 const h=render(undefined,{state:'queued'});await new Promise(setImmediate);
 assert.equal(h.node('commercial-won').getAttribute('aria-busy'),'true');
 assert.equal(h.node('commercial-open').classList.contains('metric-loading'),true);
 assert.equal(h.node('executive-revenue').textContent,'100');
 assert.equal(h.node('executive-revenue').classList.contains('metric-loading'),false);
 assert.equal(h.requests,1);
});
test('completed data with missing figures remains Pending rather than loading forever',()=>{
 const h=render({won:null,open:null,delivery:null});
 assert.equal(h.node('commercial-won').textContent,'Pendiente');
 assert.equal(h.node('commercial-won').classList.contains('metric-loading'),false);
 assert.equal(h.requests,0);
});
test('failed preparation removes the skeleton without replacing valid financial data',async()=>{
 const h=render(undefined,{state:'failed'});await new Promise(setImmediate);
 assert.equal(h.node('commercial-won').textContent,'No disponible');
 assert.equal(h.node('commercial-won').classList.contains('metric-loading'),false);
 assert.equal(h.node('commercial-won').getAttribute('aria-busy'),null);
 assert.equal(h.node('executive-revenue').textContent,'100');
 assert.equal(h.stopped,1);
});
test('a newly prepared commercial cut is applied once through a reload',async()=>{
 const h=render(undefined,{state:'ready',has_commercial_cut:true});await new Promise(setImmediate);
 assert.equal(h.reloads,1);
 assert.equal(h.stopped,1);
});
