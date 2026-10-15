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
