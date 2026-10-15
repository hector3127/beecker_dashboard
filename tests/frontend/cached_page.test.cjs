const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,
  '../../apps/portal/static/portal/js/cached_page.js'), 'utf8');

function harness(ok) {
  const state = {textContent: 'Último corte', appendChild(button) {this.button = button;}};
  const requests = [];
  let reloads = 0;
  vm.runInNewContext(source, {
    URL,
    document: {getElementById: () => state, createElement: () => ({})},
    window: {location: {href: 'http://localhost/comercial/?cliente=ACME', reload() {reloads++;}}},
    fetch: async url => {
      requests.push(url.toString());
      return {ok: true, text: async () => '<body>'};
    },
    DOMParser: class {parseFromString() {return {body: {dataset: {portalReady: ok ? 'true' : 'false'}}};}},
  });
  return {state, requests, reloads: () => reloads};
}

test('refresh prepares the new cut without resetting the visible page or filters', async () => {
  const h = harness(true);
  await new Promise(resolve => setImmediate(resolve));
  assert.match(h.requests[0], /cliente=ACME&actualizar=1/);
  assert.equal(h.reloads(), 0);
  assert.match(h.state.textContent, /Nuevo corte disponible/);
  h.state.button.onclick();
  assert.equal(h.reloads(), 1);
});

test('failed source refresh keeps the old cut and offers a retry', async () => {
  const h = harness(false);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.reloads(), 0);
  assert.equal(h.state.button, undefined);
  assert.match(h.state.textContent, /Se conserva el último corte/);
});

function executiveHarness(states) {
  const requests = [];
  let reloads = 0;
  const state = {
    dataset: {refreshUrl: '/ejecutiva/actualizacion/'},
    appendChild(button) {this.button = button;},
  };
  vm.runInNewContext(source, {
    URL,
    document: {
      getElementById: () => state,
      querySelector: () => ({value: 'csrf-token'}),
      createElement: () => ({}),
    },
    window: {
      location: {
        href: 'http://localhost/?periodo=mes&anio=2026&mes=9',
        reload() {reloads++;},
      },
      addEventListener() {},
    },
    setTimeout: callback => callback(),
    fetch: async (url, options) => {
      requests.push({url: String(url), options});
      return {ok: true, json: async () => states.shift()};
    },
  });
  return {state, requests, reloads: () => reloads};
}

test('executive refresh polls a light status endpoint and retains dates and CSRF', async () => {
  const h = executiveHarness([
    {state: 'queued'}, {state: 'running'}, {state: 'ready', partial: false},
  ]);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.requests.length, 3);
  assert.match(h.requests[0].url, /actualizacion\/\?periodo=mes&anio=2026&mes=9/);
  assert.equal(h.requests[0].options.method, 'POST');
  assert.equal(h.requests[0].options.headers['X-CSRFToken'], 'csrf-token');
  assert.equal(h.requests[1].options.cache, 'no-store');
  assert.equal(h.reloads(), 0);
  assert.match(h.state.textContent, /Nuevo corte disponible/);
  h.state.button.onclick();
  assert.equal(h.reloads(), 1);
});

test('executive partial and failed refreshes do not claim a complete cut', async () => {
  const partial = executiveHarness([{state: 'ready', partial: true}]);
  const failed = executiveHarness([{state: 'running'}, {state: 'failed'}]);
  await new Promise(resolve => setImmediate(resolve));
  assert.match(partial.state.textContent, /corte parcial/);
  assert.ok(partial.state.button);
  assert.match(failed.state.textContent, /Se conserva el último corte/);
  assert.equal(failed.state.button, undefined);
  assert.equal(failed.reloads(), 0);
});
