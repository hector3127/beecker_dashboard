/* No browser dependency: exercise request ordering and live-node ownership. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,
  '../../apps/portal/static/portal/js/operativa.js'), 'utf8');
const ids = ['ops-refresh-status', 'ops-refresh-button', 'facturability-summary',
  'ops-investment-operational', 'ops-investment-commercial', 'ops-capacity',
  'ops-metric-progress', 'ops-metric-paused', 'ops-metric-on-time',
  'ops-health', 'ops-managers', 'ops-evas', 'ops-eva4-card'];

class Node {
  constructor(id, parent) {
    this.id = id;
    this.parent = parent;
    this.textContent = '';
    this.dataset = {};
    this.attributes = {};
    this.children = [];
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  querySelector(selector) {
    if (selector === '[data-operations-summary]') return this.children[0] || null;
    if (selector.startsWith('#')) return this.nodes?.get(selector.slice(1)) || null;
    return null;
  }
  querySelectorAll(selector) { return selector === '[data-investment]' ? this.children : []; }
  replaceChildren(node) { this.children = [node]; }
  replaceWith(next) {
    if (this.id === 'ops-dashboard') {
      next.live = this.live;
      this.live.root = next;
    } else {
      this.parent.nodes.set(this.id, next);
      next.parent = this.parent;
    }
  }
  focus() {}
}

function dashboard(options = {}) {
  const root = new Node('ops-dashboard');
  root.dataset = {async: 'true', endpoint: '/operativa/datos/',
    summaryEndpoint: '/operations/resumen/', sourceErrors: '0', loadedAt: '13/10/2026, 10:00',
    ...options};
  root.nodes = new Map(ids.map(id => [id, new Node(id, root)]));
  return root;
}
function doc(root) {
  return {getElementById: id => id === root.id ? root : root.nodes.get(id)};
}
function fragment(partial = false) {
  const summary = new Node('summary');
  summary.dataset.partial = String(partial);
  return {summary, querySelector: () => summary};
}
function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
}
function harness(options = {}) {
  const live = {root: dashboard(options.initial)};
  live.root.live = live;
  const listeners = {};
  const requests = [];
  const freshness = new Node('portal-freshness-text');
  const document = {
    activeElement: null,
    querySelectorAll: selector => selector === '[data-investment-projects]'
      ? live.root.nodes.get('ops-managers').children : [],
    getElementById: id => id === 'portal-freshness-text' ? freshness
      : id === 'ops-dashboard' ? live.root : live.root.nodes.get(id),
    addEventListener: (name, callback) => { listeners[name] = callback; }
  };
  vm.runInNewContext(source, {
    document, location: {search: '', href: 'http://localhost/operativa/', origin: 'http://localhost', assign() {}},
    window: {addEventListener() {}}, URL, URLSearchParams, AbortController, setTimeout, clearTimeout,
    matchMedia: () => ({matches: false}),
    DOMParser: class {parseFromString(value) { return value; }},
    fetch: async url => {
      requests.push(url);
      const block = new URL(url, 'http://localhost').searchParams.get('bloque') || 'base';
      const payload = url.startsWith('/operations/') ? fragment(options.partialSummary)
        : doc(dashboard(block === options.failedBlock ? {blockError: 'No disponible'}
          : block === 'base' && options.partialPortfolio ? {sourceErrors: '1'} : {}));
      if (options.handle) return options.handle(url, payload);
      return {ok: true, redirected: options.redirect, text: async () => payload};
    }
  });
  return {live, requests, listeners, document, freshness};
}
async function settled() {
  for (let i = 0; i < 20; i++) await new Promise(setImmediate);
}

test('summary arriving first survives replacement and EVA cannot overwrite investment', async () => {
  const release = deferred();
  const h = harness({handle: async (url, payload) => {
    if (url === '/operativa/datos/?') await release.promise;
    if (url.includes('bloque=eva3')) await new Promise(setImmediate);
    if (url.includes('bloque=inversion')) {
      payload.getElementById('ops-dashboard').nodes.get('ops-investment-operational').textContent = '42 h';
    }
    return {ok: true, text: async () => payload};
  }});
  await settled();
  const summary = h.document.getElementById('facturability-summary');
  assert.equal(summary.children.length, 1);
  release.resolve();
  await settled();
  assert.equal(h.document.getElementById('facturability-summary'), summary);
  assert.equal(h.document.getElementById('ops-investment-operational').textContent, '42 h');
  assert.equal(h.document.getElementById('ops-refresh-button').disabled, false);
  assert.equal(h.document.getElementById('ops-refresh-button').hidden, false);
  assert.match(h.document.getElementById('ops-refresh-status').textContent, /Consulta completada/);
  assert.equal(h.requests.length, 6);
});

test('summary arriving after replacement updates the connected node', async () => {
  const release = deferred();
  const h = harness({handle: async (url, payload) => {
    if (url.startsWith('/operations/')) await release.promise;
    return {ok: true, text: async () => payload};
  }});
  await settled();
  release.resolve();
  await settled();
  assert.equal(h.document.getElementById('facturability-summary').children.length, 1);
  assert.equal(h.document.getElementById('facturability-summary').attributes['aria-busy'], 'false');
});

test('source and block failures report partial completion and enable retry', async () => {
  const h = harness({partialPortfolio: true, partialSummary: true, failedBlock: 'capacidad'});
  const oldCapacity = h.document.getElementById('ops-capacity');
  await settled();
  const status = h.document.getElementById('ops-refresh-status').textContent;
  assert.match(status, /Actualización parcial/);
  assert.match(status, /fuentes del portafolio/);
  assert.match(status, /capacidad/);
  assert.match(status, /facturabilidad/);
  assert.notEqual(h.document.getElementById('ops-capacity'), oldCapacity);
  assert.equal(h.document.getElementById('ops-refresh-button').disabled, false);
});

test('authentication redirects never replace the dashboard', async () => {
  const h = harness({redirect: true});
  const original = h.live.root;
  await settled();
  assert.equal(h.live.root, original);
  assert.match(h.document.getElementById('ops-refresh-status').textContent, /Actualización parcial/);
});

test('repeated clicks during a refresh do not duplicate requests', async () => {
  const release = deferred();
  const h = harness({handle: async (url, payload) => {
    await release.promise;
    return {ok: true, text: async () => payload};
  }});
  const click = {target: {closest: selector => selector === '#ops-refresh-button' ? {} : null}};
  h.listeners.click(click);
  h.listeners.click(click);
  assert.equal(h.requests.length, 2);
  release.resolve();
  await settled();
  assert.equal(h.requests.length, 6);
  h.listeners.click(click);
  await settled();
  assert.equal(h.requests.length, 12);
});

test('fresh navigation makes no requests and manual refresh still updates all blocks', async () => {
  const h = harness({initial: {async: 'false', summaryFresh: 'true'}});
  await settled();
  assert.equal(h.requests.length, 0);
  assert.equal(h.document.getElementById('ops-refresh-button').hidden, false);
  h.listeners.click({target: {closest: selector => selector === '#ops-refresh-button' ? {} : null}});
  await settled();
  assert.equal(h.requests.length, 6);
  assert.ok(h.requests.includes('/operations/resumen/?actualizar=1'));
});

test('only stale facturability loads when the portfolio is fresh', async () => {
  const h = harness({initial: {async: 'false', summaryFresh: 'false'}});
  await settled();
  assert.deepEqual(h.requests, ['/operations/resumen/']);
});

test('entering Operativa does not prefetch manager details', async () => {
  const h = harness({initial: {async: 'false', summaryFresh: 'true'}});
  await settled();
  assert.equal(h.requests.length, 0);
  assert.equal(h.listeners.pointerover, undefined);
  assert.equal(h.listeners.focusin, undefined);
});

test('automatic refresh requests only expired blocks', async () => {
  const h = harness({initial: {pendingBlocks: 'capacidad', summaryFresh: 'true'}});
  await settled();
  assert.deepEqual(h.requests, ['/operativa/datos/?', '/operativa/datos/?bloque=capacidad']);
});

for (const first of ['inversion', 'eva3']) {
  test(`DM investment survives ${first} finishing before the other block`, async () => {
    const release = deferred();
    const second = first === 'inversion' ? 'eva3' : 'inversion';
    const h = harness({handle: async (url, payload) => {
      if (url.includes('bloque=' + second)) await release.promise;
      if (url.includes('bloque=eva3')) {
        const card = new Node('investment-card');
        card.dataset.investmentProjects = JSON.stringify(['IXB.1', 'IXB.2']);
        card.children = ['commercial', 'operational'].map(kind => {
          const value = new Node(kind); value.dataset.investment = kind; return value;
        });
        payload.getElementById('ops-dashboard').nodes.get('ops-managers').children = [card];
      }
      if (url.includes('bloque=inversion')) {
        const data = new Node('ops-investment-data');
        data.textContent = JSON.stringify({complete: true, by_project: {
          'IXB.1': {commercial: 2.5, operational: 8},
          'IXB.2': {commercial: 3, operational: 0},
          'OTHER': {commercial: 100, operational: 100}
        }});
        payload.getElementById('ops-dashboard').nodes.set(data.id, data);
      }
      return {ok: true, text: async () => payload};
    }});
    await settled(); release.resolve(); await settled();
    const values = h.document.getElementById('ops-managers').children[0].children;
    assert.equal(values[0].textContent, '5.5 h');
    assert.equal(values[1].textContent, '8 h');
    assert.equal(h.requests.length, 6);
  });
}
