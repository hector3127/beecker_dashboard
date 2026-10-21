const {test}=require('node:test');
const assert=require('node:assert/strict');
const domState=require('./dom_state.cjs');
const {isLoadingMessage,begin,inspect}=require('../../apps/portal/static/portal/js/portal_loading.js');

test('loading distinguishes an in-flight query from missing business data',()=>{
 for(const message of ['Consultando…','Preparando corte del periodo…','Cargando datos','Guardando estado…'])assert.equal(isLoadingMessage(message),true);
 for(const message of ['Pendiente','No disponible','Sin presupuesto','0','31 costos pendientes','Sin acuerdos registrados'])assert.equal(isLoadingMessage(message),false);
});
test('overlapping queries retain the loading marker until the last one ends',()=>{
 const target=domState(),first=begin(target),second=begin(target);
 assert.equal(target.getAttribute('aria-busy'),'true');
 first();first();
 assert.equal(target.classList.contains('portal-loading-region'),true);
 second();
 assert.equal(target.classList.contains('portal-loading-region'),false);
 assert.equal(target.getAttribute('aria-busy'),'false');
});
test('rendered text loses its skeleton when a result or missing value arrives',()=>{
 const target={...domState(),matches(){return true;},closest(){return null;},childElementCount:0,textContent:'Consultando…'};
 inspect(target);assert.equal(target.classList.contains('portal-loading-message'),true);
 target.textContent='Pendiente';inspect(target);
 assert.equal(target.classList.contains('portal-loading-message'),false);
});
