const {test}=require('node:test');
const assert=require('node:assert/strict');
const {selectBillingMonth}=require('../../apps/portal/static/portal/js/facturability_selection.js');
function fixture(){
 const nodes=new Map();const node=key=>{if(!nodes.has(key))nodes.set(key,{textContent:'',style:{}});return nodes.get(key);};
 const root={dataset:{target:'70',latestMonth:'2026-09',monthClosed:'true'},querySelector:node,querySelectorAll:()=>bars};
 const bars=[{billingMonth:'2026-08',label:'Agosto 2026',percent:'83',fixed:'40',variable:'71'},
 {billingMonth:'2026-09',label:'Septiembre 2026',percent:'87.07',fixed:'47',variable:'75'},
 {billingMonth:'2026-06',label:'Junio 2026',percent:'',fixed:'',variable:''}].map(dataset=>({dataset,closest:()=>root,setAttribute(k,v){this[k]=v;},querySelector:()=>({setAttribute(){}})}));
 return {node,bars};
}
test('month clicks update the exact global value, components, target and selected bar',()=>{
 const h=fixture();selectBillingMonth(h.bars[0]);
 assert.equal(h.node('[data-billing-value]').textContent,'83%');
 assert.equal(h.node('[data-billing-fixed]').textContent,'AER 40%');
 assert.match(h.node('[data-billing-gap]').textContent,/13 puntos arriba/);
 assert.equal(h.node('[data-billing-label]').textContent,'Agosto 2026 · mes seleccionado');
 assert.equal(h.bars[0]['aria-pressed'],'true');
 selectBillingMonth(h.bars[1]);assert.equal(h.node('[data-billing-value]').textContent,'87.07%');
 assert.match(h.node('[data-billing-label]').textContent,/último mes cerrado/);
 assert.equal(h.bars[0]['aria-pressed'],'false');
});
test('missing monthly figures stay unavailable and are never converted to zero',()=>{
 const h=fixture();selectBillingMonth(h.bars[2]);
 assert.equal(h.node('[data-billing-value]').textContent,'—');
 assert.equal(h.node('[data-billing-variable]').textContent,'PRJ —');
 assert.match(h.node('[data-billing-gap]').textContent,/Sin datos/);
});
