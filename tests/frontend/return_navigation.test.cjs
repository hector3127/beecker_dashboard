const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../../apps/portal/static/portal/js/return_navigation.js'),'utf8');
function run(href,target,back=false){
 const location=new URL(href), listeners={};
 const link={href:target,hasAttribute:key=>back&&key==='data-portal-back',classList:{contains:()=>false}};
 vm.runInNewContext(source,{URL,URLSearchParams,location,document:{addEventListener:(name,fn)=>listeners[name]=fn,getElementById:()=>null}});
 listeners.click({target:{closest:()=>link}});
 return new URL(link.href);
}
test('list to costs preserves filters and period as immediate parent',()=>{
 const parent='http://localhost/ejecutiva/cuentas/?periodo=mes&anio=2026&mes=10&buscar=Heineken';
 const url=run(parent,'http://localhost/ejecutiva/costos/detalle/?nombre=Heineken');
 assert.equal(url.searchParams.get('volver'),new URL(parent).pathname+new URL(parent).search);
 assert.equal(url.searchParams.get('mes'),'10');
});
test('account to costs preserves the nested list return chain',()=>{
 const parent='http://localhost/cuenta/a/?nombre=A&volver=%2Fejecutiva%2Fcuentas%2F';
 const url=run(parent,'http://localhost/ejecutiva/costos/detalle/?nombre=A');
 assert.equal(url.searchParams.get('volver'),new URL(parent).pathname+new URL(parent).search);
});
test('return links and external links are never rewritten',()=>{
 const target='http://localhost/cuenta/a/?nombre=A&volver=%2Fejecutiva%2Fcuentas%2F';
 assert.equal(run('http://localhost/ejecutiva/costos/detalle/',target,true).href,target);
 assert.equal(run('http://localhost/', 'https://other.test/cuenta/a/').href,'https://other.test/cuenta/a/');
});

test('account list restores search and classification and saves changes in its URL',()=>{
 const location=new URL('http://localhost/ejecutiva/cuentas/?periodo=anio&anio=2026&buscar=Heineken&clasificacion=pending');
 const elements=Object.fromEntries(['account-search','account-filter'].map(id=>[id,{value:'',listeners:{},addEventListener(name,fn){this.listeners[name]=fn;},dispatchEvent(event){this.dispatched=event.type;}}]));
 let saved;
 vm.runInNewContext(source,{URL,URLSearchParams,location,Event:class{constructor(type){this.type=type;}},history:{state:null,replaceState:(state,title,url)=>saved=url},document:{addEventListener(){},getElementById:id=>elements[id]}});
 assert.equal(elements['account-search'].value,'Heineken');
 assert.equal(elements['account-filter'].value,'pending');
 assert.equal(elements['account-search'].dispatched,'input');
 elements['account-search'].value='Otra cuenta';elements['account-search'].listeners.input();
 const url=new URL(saved,location);assert.equal(url.searchParams.get('buscar'),'Otra cuenta');assert.equal(url.searchParams.get('anio'),'2026');
});
