const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');
let template=fs.readFileSync(require('node:path').join(__dirname,'../../apps/portal/templates/portal/costos_detalle.html'),'utf8');
const source=template.split('{% block scripts %}<script>')[1].split('</script>')[0]
 .replace('{% url "portal:proyecto_detalle" "project-placeholder" %}','/proyectos/project-placeholder/')
 .replace('{% url "portal:costos_revenue" %}','/ejecutiva/costos/');

test('cost project IDs link to their detail in the same tab with the full return chain',async()=>{
 const ids=['AER.MCC.004','MCC.014_CR2','CCO.001 | CR'];
 const nodes=new Map();
 const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:id==='cost-filter'?'all':'',innerHTML:'',textContent:'',scrollIntoView(){},addEventListener(){}});return nodes.get(id);}};
 const location=new URL('http://localhost/ejecutiva/costos/detalle/?nombre=Heineken&periodo=anio&anio=2026&volver=%2Fejecutiva%2Fcuentas%2F');
 vm.runInNewContext(source,{document,window:{location},URL,URLSearchParams,fetch:async()=>({ok:true,json:async()=>({projects:ids.map(id=>({id,hours:2,cost:3,complete:true})),pending:0,cost:9,deduplicated_entries:3,band_month:'2026-10'})})});
 for(let i=0;i<5;i++)await new Promise(setImmediate);
 const html=nodes.get('cost-audit-body').innerHTML;
 const hrefs=[...html.matchAll(/class="cost-project-link" href="([^"]+)"/g)].map(m=>m[1].replaceAll('&amp;','&'));
 assert.equal(hrefs.length,3);
 hrefs.forEach((href,i)=>{const url=new URL(href,location);assert.equal(decodeURIComponent(url.pathname),'/proyectos/'+ids[i]+'/');assert.equal(url.searchParams.get('volver'),location.pathname+location.search);});
 assert.ok(!html.includes('target='));
 assert.match(html,/data-persons="AER.MCC.004"/);
});


test('error and pending IDs explain unavailability; zero and partial costs remain usable',async()=>{
 const projects=[{id:'BAD.001',hours:null,cost:null,error:'Sin coincidencia'}, {id:'PENDING.001',cost:null}, {id:'ERROR.002',cost:10,error:'Fuente no disponible'}, {id:'ZERO.001',hours:0,cost:0,complete:true}, {id:'PARTIAL.001',hours:2,cost:20,complete:false}];
 const nodes=new Map();const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:id==='cost-filter'?'all':'',innerHTML:'',textContent:'',scrollIntoView(){},addEventListener(){}});return nodes.get(id);}};
 const location=new URL('http://localhost/ejecutiva/costos/detalle/');
 vm.runInNewContext(source,{document,window:{location},URL,URLSearchParams,fetch:async()=>({ok:true,json:async()=>({projects,pending:2,cost:30,deduplicated_entries:2,band_month:'2026-10'})})});
 for(let i=0;i<5;i++)await new Promise(setImmediate);
 const html=nodes.get('cost-audit-body').innerHTML;
 for(const id of ['BAD.001','PENDING.001','ERROR.002']){assert.ok(html.includes('data-project-unavailable="'+id+'"'));assert.ok(!html.includes('aria-label="Ver proyecto '+id+'"'));}
 for(const id of ['ZERO.001','PARTIAL.001'])assert.ok(html.includes('aria-label="Ver proyecto '+id+'"'));
 await nodes.get('cost-audit-body').onclick({target:{closest:selector=>selector==='[data-project-unavailable]'?{dataset:{projectUnavailable:'BAD.001',projectError:'Sin coincidencia en Clockify'}}:null}});
 assert.equal(nodes.get('cost-project-notice').hidden,false);
 assert.match(nodes.get('cost-project-notice').textContent,/No es posible abrir el proyecto BAD\.001/);
 assert.match(nodes.get('cost-project-notice').textContent,/Sin coincidencia en Clockify/);

});
