const domState=require('./dom_state.cjs');
const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('apps/portal/static/portal/js/executive_numbers.js','utf8')+'\n'+fs.readFileSync('apps/portal/static/portal/js/executive_report.js','utf8');
function run(complete){const nodes=new Map();const get=id=>{if(!nodes.has(id))nodes.set(id,{...domState(),textContent:'',innerHTML:'',dataset:{url:'/ejecutiva/costos/detalle/',endpoint:'/ejecutiva/actualizacion/'}});return nodes.get(id);};get('financial-cache').textContent=JSON.stringify({loaded_at:'2026-10-19T12:00:00',revenue:{invoiced:1897644.14,collections_percent:68},costs:{cost:500000,complete,projects:[{id:'A',cost:500000,complete},{id:'B',cost:null,complete:false}]},accounts:{healthy:[],unhealthy:[],pending_accounts:0},commercial:{won:1490000,won_count:4}});get('operations-cache').textContent=JSON.stringify({partial:false,etc:36890,advance:40.58,fte:34.16,projects:10,facturability:75.2,investment_operational:111.8});let requests=0;vm.runInNewContext(source,{document:{getElementById:get},location:{href:'http://localhost/',search:''},URL,fetch:()=>{requests++;throw Error('No request on prepared cut');}});return {get,requests};}
test('prepared executive cut performs no API calls and formats consistent thousands',()=>{const h=run(true);assert.equal(h.requests,0);assert.equal(h.get('executive-revenue').textContent,'1.89M');assert.equal(h.get('commercial-won').textContent,'1.49M');assert.equal(h.get('executive-ops-advance').textContent,'41%');assert.equal(h.get('executive-ops-etc').textContent,'36,890 h');assert.equal(h.get('executive-margin').textContent,'74%');assert.match(h.get('commercial-delivery-note').textContent,/Poly/);});
test('available costs publish a clearly marked partial margin without further queries',()=>{const h=run(false);assert.equal(h.get('executive-margin').textContent,'74%*');assert.match(h.get('executive-margin-note').textContent,/Parcial con costos disponibles/);assert.equal(h.requests,0);});


test('first load applies actual prepared data once; source failures never cause a reload loop',async()=>{
 for(const available of [true,false]){
  const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,{...domState(),textContent:'{}',innerHTML:'',dataset:{endpoint:'/ejecutiva/actualizacion/'}});return nodes.get(id);};
  let reloads=0,cleared=0;
  vm.runInNewContext(source,{document:{getElementById:get},location:{href:'http://localhost/',search:'',reload:()=>reloads++},URL,setInterval:()=>1,clearInterval:()=>cleared++,fetch:async()=>({ok:true,json:async()=>({state:'ready',partial:true,has_financial_cut:available})})});
  await new Promise(setImmediate);assert.equal(reloads,available?1:0);assert.equal(cleared,1);
 }
});
