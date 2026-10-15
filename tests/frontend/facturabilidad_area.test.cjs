const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../apps/portal/static/portal/js/facturabilidad_area.js'), 'utf8');

function harness() {
  const nodes = new Map(), requests = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {id, style: {}, value: '', dataset: {year: '2025'},
      children: [], innerHTML: '', textContent: '', className: '',
      classList: {toggle() {}, add() {}, remove() {}},
      querySelector(selector) {return node(selector);}, querySelectorAll() {return [];},
      appendChild(child) {nodes.set(child.id, child); this.children.push(child);},
      focus() {}, setAttribute() {}});
    return nodes.get(id);
  }
  function runner(success, failure) {
    return {withSuccessHandler(fn) {return runner(fn, failure);},
      withFailureHandler(fn) {return runner(success, fn);},
      gseObtenerAreas() {requests.push({success, failure});}};
  }
  const context = {document: {getElementById: id => id === 'gse-panel' || id === 'gse-section-content' ? nodes.get(id) : node(id),
    createElement: () => ({...node('created'), children: []})},
    location: {hash: '', search: ''}, Date, setTimeout, clearTimeout,
    google: {script: {run: runner()}}, addEventListener() {}};
  context.window = context;
  vm.runInNewContext(source, context);
  return {context, node, requests};
}

test('GSE mounts in its own portal host and loads only area metadata initially', () => {
  const h = harness();
  assert.equal(h.requests.length, 1);
  assert.equal(h.node('gse-host').children[0].id, 'gse-panel');
  assert.match(h.node('gse-panel').innerHTML, /value="2025"/);
  h.requests[0].success({ok: true, areas: ['DEV', 'QA']});
  assert.equal(h.node('gse-load').disabled, false);
  assert.match(h.node('gse-area').innerHTML, /DEV/);
  assert.equal(h.requests.length, 1);
  h.context.gseCambiarApartado('hours');
  assert.equal(h.node('gse-section-content').style.display, '');
  assert.match(h.node('gse-section-content').innerHTML, /gse-hours-table/);
});

test('area source errors are displayed without inventing data', () => {
  const h = harness();
  h.requests[0].success({ok: false, error: 'Falta ROL'});
  assert.equal(h.node('gse-status').textContent, 'Falta ROL');
  assert.equal(h.node('gse-load').disabled, true);
});
