const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

test('account loads its formatter and displays all financial cards',async()=>{
  const html=fs.readFileSync('apps/portal/templates/portal/cuenta.html','utf8');
  const marker=html.indexOf("portal/js/executive_numbers.js");
  const inline=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].find(m=>m[1].includes('cuenta_financiera'));
  assert.ok(marker>=0 && marker<inline.index,'Formatter must be loaded before financial cards');
  const nodes=new Map();
  const get=id=>{if(!nodes.has(id))nodes.set(id,{textContent:''});return nodes.get(id);};
  const context={document:{getElementById:get},fetch:async()=>({ok:true,json:async()=>({account:{revenue:53950,cost:11050.45,margin:79.52,pending:0,projects:1,collected:48555,invoiced:53950,collections_percent:90}})})};
  vm.runInNewContext(fs.readFileSync('apps/portal/static/portal/js/executive_numbers.js','utf8')+'\n'+inline[1],context);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(get('account-finance-revenue').textContent,'53K');
  assert.equal(get('account-finance-margin').textContent,'79.52%');
  assert.equal(get('account-finance-collections').textContent,'90%');
  assert.ok(!get('account-finance-revenue-note').textContent.includes('No se pudo'));
});
