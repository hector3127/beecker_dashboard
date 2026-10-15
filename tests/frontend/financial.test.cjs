const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname,
  '../../apps/portal/templates/portal/ejecutiva.html'), 'utf8');
const source = fs.readFileSync(path.join(__dirname,
  '../../apps/portal/static/portal/js/executive_monthly_chart.js'), 'utf8') + '\n' + [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).join('\n');

function harness(seed, search = "", background = false) {
  const nodes = new Map();
  const listeners = {};
  const requests = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {textContent: '', style: {}, dataset: {},
      innerHTML: '', showModal() {this.open = true;}, close() {this.open = false;}});
    return nodes.get(id);
  }
  node('financial-cache').textContent = JSON.stringify({...seed, commercial:seed.commercial||{won:100,open:200,won_count:1,open_count:2,pending_usd:0},
    accounts: seed.accounts || {healthy: [], unhealthy: [], pending_accounts: 0}});
  node('operations-cache').textContent = JSON.stringify({budget: 100, advance: 20,
    etc: 80, projects: 1, known_projects: 1, missing_budget: 0, partial: false, pending_ids: background ? ['A'] : []});
  if (background) node('cached-page-state').dataset.refreshUrl = '/ejecutiva/actualizacion/';
  const context = {URL, URLSearchParams, document: {getElementById: node}, window: {
    location: {search, href: "http://localhost/" + search},
    addEventListener: (name, fn) => {
      const previous = listeners[name];
      listeners[name] = () => {previous?.(); fn();};
    },
    dispatchEvent: event => listeners[event.type]?.(),
    open: () => {},
  }, fetch: async url => {requests.push(url); throw Error('Unexpected download');},
  Event: class {constructor(type) {this.type = type;}}};
  vm.runInNewContext(source, context);
  return {context, node, requests, listeners};
}

test('accounts with costs and no revenue display a USD loss instead of a zero margin', async () => {
  const h = harness({revenue:{total:'0'},costs:{cost:100,complete:true,projects:[]},
    profitability:{months:[],complete:true},
    accounts:{healthy:[],unhealthy:[{name:'Gift',url:'/cuenta/gift/',revenue:0,
      cost:100,gross_profit:-100,margin:null,projects:1}],pending_accounts:0}});
  await new Promise(setImmediate);
  const html = h.node('unhealthy-financial-accounts').innerHTML;
  assert.match(html,/USD \$-100/);
  assert.match(html,/Sin ingresos/);
  assert.doesNotMatch(html,/<strong>0%/);
});

test('executive rankings show five rows and identify the full available count', async () => {
  const accounts=Array.from({length:8},(_,i)=>({name:'Account '+i,url:'/cuenta/'+i+'/',
    revenue:100,cost:90,gross_profit:10,margin:10,projects:1}));
  const h=harness({revenue:{total:'800'},costs:{cost:720,complete:true,projects:[]},
    profitability:{months:[],complete:true},accounts:{healthy:[],unhealthy:accounts,pending_accounts:0}});
  await new Promise(setImmediate);
  assert.equal((h.node('unhealthy-financial-accounts').innerHTML.match(/class="ranking-account"/g)||[]).length,5);
  assert.match(h.node('unhealthy-account-count').textContent,/5 cuentas de 8/);
  assert.equal((html.match(/class="ranking-all"/g)||[]).length,1);
  assert.match(html,/class="ranking-section-heading"/);
  assert.doesNotMatch(html,/Clasificación y cobertura de cuentas|account-profitability-note/);
});

test('prepared financial page renders margin and chart without API requests', async () => {
  const seed = {
    revenue: {total: '200', collections_percent: 50},
    costs: {cost: 100, complete: true, pending: 0, band_month: '2026-10',
      projects: [{id: 'AIN.002 CR', cost: 100, hours: 10, complete: true}]},
    profitability: {complete: true, band_month: '2026-10', pending_projects: 0,
      months: [{month: '2026-09', revenue: 200, cost: 100, gross_profit: 100, margin: 50, partial: false}]},
  };
  const h = harness(seed);
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(h.requests, []);
  assert.equal(h.node('executive-margin').textContent, '50%');
  assert.equal(h.node('executive-collections').textContent, '50%');
  assert.match(h.node('executive-cost').textContent, /100/);
  assert.match(h.node('monthly-profit-chart').innerHTML, /<svg/);
  assert.equal(h.node('monthly-profit-state').textContent, 'Datos reales');
});

test('background refresh prevents duplicate per-project Clockify calculations', async () => {
  const h = harness({
    revenue: {total: '100'},
    costs: {cost: 0, complete: false, pending: 1, projects: [{id: 'A', cost: null}]},
    profitability: {months: [], complete: false},
  }, '', true);
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(h.requests, []);
  assert.match(h.node('executive-ops-budget').textContent, /100/);
});

test('partial costs show provisional margin and refresh the monthly chart', async () => {
  const h = harness({
    revenue: {total: '100', collections_percent: null},
    costs: {cost: 150, complete: false, pending: 0, band_month: '2026-10',
      projects: [{id: 'X', cost: 150, hours: 10, complete: false}]},
    profitability: {complete: false, band_month: '2026-10', pending_projects: 0,
      months: [{month: '2026-09', revenue: 100, cost: 150, gross_profit: -50, margin: -50, partial: true}]},
  });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.node('executive-margin').textContent, '-50%*');
  assert.match(h.node('executive-margin-note').textContent, /Provisional/);
  assert.equal(h.node('executive-collections').textContent, 'Sin dato');
  h.listeners['financial-costs-updated']();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.requests.length, 2);
  assert.match(h.requests[0], /rentabilidad_mensual/);
  assert.match(h.requests[1], /cuentas_rentabilidad/);
});


test('executive requests preserve the selected range and project ID', async () => {
  const h = harness({revenue:{total:'0'},costs:{cost:0,complete:true,projects:[]},profitability:{months:[],complete:true}},
    '?periodo=rango&desde=2026-04-10&hasta=2026-04-15');
  await assert.rejects(()=>h.context.executiveFetch('/costs/?id=TEST'));
  const request = new URL(h.requests.at(-1));
  assert.equal(request.searchParams.get('id'),'TEST');
  assert.equal(request.searchParams.get('desde'),'2026-04-10');
  assert.equal(request.searchParams.get('hasta'),'2026-04-15');
  assert.equal(request.searchParams.get('periodo'),'rango');
});


test('commercial card uses real totals and does not invent delivery balance',async()=>{
 const h=harness({commercial:{won:1500,open:4000,won_count:2,open_count:3,pending_usd:1},
 revenue:{total:'0'},costs:{cost:0,complete:true,projects:[]},profitability:{months:[],complete:true}});
 await new Promise(resolve=>setTimeout(resolve,20));
 assert.match(h.node('commercial-won').textContent,/USD/);
 assert.equal(h.node('commercial-delivery').textContent,'Sin dato');
 assert.equal(h.node('commercial-data-state').textContent,'Datos parciales');
 assert.match(h.node('commercial-won-note').textContent,/2 ventas/);
});
