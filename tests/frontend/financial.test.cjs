const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname,
  '../../apps/portal/templates/portal/ejecutiva.html'), 'utf8');
const source = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).join('\n');

function harness(seed) {
  const nodes = new Map();
  const listeners = {};
  const requests = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {textContent: '', style: {}, dataset: {},
      innerHTML: '', showModal() {this.open = true;}, close() {this.open = false;}});
    return nodes.get(id);
  }
  node('financial-cache').textContent = JSON.stringify(seed);
  const context = {document: {getElementById: node}, window: {
    addEventListener: (name, fn) => listeners[name] = fn,
    dispatchEvent: event => listeners[event.type]?.(),
    open: () => {},
  }, fetch: async url => {requests.push(url); throw Error('Unexpected download');},
  Event: class {constructor(type) {this.type = type;}}};
  vm.runInNewContext(source, context);
  return {context, node, requests, listeners};
}

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
  assert.equal(h.requests.length, 1);
  assert.match(h.requests[0], /rentabilidad_mensual/);
});
