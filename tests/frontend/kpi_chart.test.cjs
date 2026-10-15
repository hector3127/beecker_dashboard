const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../apps/portal/static/portal/js/kpi_chart.js'), 'utf8');

function harness(series) {
  function node(tag) {
    return {tag, children: [], attrs: {}, style: {}, textContent: '',
      setAttribute(k, v) {this.attrs[k] = v;}, appendChild(el) {this.children.push(el);},
      append(...els) {this.children.push(...els);}, replaceChildren() {this.children = [];}};
  }
  const nodes = Object.fromEntries(['kpi-chart-data', 'kpi-chart', 'kpi-legend', 'kpi-chart-toggle', 'kpi-chart-scale'].map(id => [id, node(id)]));
  nodes['kpi-chart-data'].textContent = JSON.stringify({labels: ['Ene', 'Feb', 'Oct*'], highlight: ['Oct*'], series});
  vm.runInNewContext(source, {document: {getElementById: id => nodes[id], createElementNS: (_, tag) => node(tag), createElement: node}});
  return nodes;
}

test('similar percentages have a labelled expanded scale and can be isolated', () => {
  const n = harness([{name: 'Ana', values: [69, 70, 73]}, {name: 'Luis', values: [71, 72, 74]}]);
  const svg = n['kpi-chart'];
  assert.equal(n['kpi-chart-scale'].textContent, 'Escala ampliada: 60–80%');
  assert.equal(svg.children.filter(x => x.tag === 'path').length, 2);
  n['kpi-legend'].children[0].onclick();
  assert.equal(svg.children.filter(x => x.tag === 'path').length, 1);
  assert.equal(n['kpi-legend'].children[0].attrs['aria-pressed'], 'true');
  n['kpi-chart-toggle'].onclick();
  assert.equal(n['kpi-chart-scale'].textContent, 'Escala completa: 0–100%');
  n['kpi-legend'].children[0].onclick();
  assert.equal(svg.children.filter(x => x.tag === 'path').length, 2);
  assert.equal(svg.children.filter(x => x.tag === 'rect').length, 1);
});

test('the scale preserves real zeros, missing months and values above 100%', () => {
  const n = harness([{name: 'Ana', values: [0, null, 120]}]);
  const children = n['kpi-chart'].children;
  const line = children.find(x => x.tag === 'path');
  assert.equal((line.attrs.d.match(/M/g) || []).length, 2);
  assert.doesNotMatch(line.attrs.d, /L/);
  assert.equal(children.filter(x => x.tag === 'circle').length, 2);
  assert.equal(n['kpi-chart-scale'].textContent, 'Escala ampliada: 0–130%');
  n['kpi-chart-toggle'].onclick();
  assert.equal(n['kpi-chart-scale'].textContent, 'Escala completa: 0–120%');
});
