const {test} = require('node:test');
const assert = require('node:assert/strict');

async function harness(t, series) {
  const previous = global.document;
  t.after(() => { global.document = previous; });
  const nodes = {};
  function node(tag) {
    return {tag, children: [], attrs: {}, style: {}, textContent: '',
      setAttribute(k, v) {this.attrs[k] = v;if(k==='id')nodes[v]=this;}, appendChild(el) {this.children.push(el);},
      addEventListener(name, handler) {this['on'+name]=handler;},
      append(...els) {this.children.push(...els);}, replaceChildren() {this.children = [];}};
  }
  global.document = {createElementNS: (_, tag) => node(tag), createElement: node};
  const { renderChart } = await import('../../frontend/static/scripts/pages/kpis_dm/sections/chart.js');
  renderChart({labels: ['Ene', 'Feb', 'Oct*'], highlight: ['Oct*'], series});
  return nodes;
}

test('similar percentages have a labelled expanded scale and can be isolated', async (t) => {
  const n = await harness(t, [{name: 'Ana', values: [69, 70, 73]}, {name: 'Luis', values: [71, 72, 74]}]);
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

test('the scale preserves real zeros, missing months and values above 100%', async (t) => {
  const n = await harness(t, [{name: 'Ana', values: [0, null, 120]}]);
  const children = n['kpi-chart'].children;
  const line = children.find(x => x.tag === 'path');
  assert.equal((line.attrs.d.match(/M/g) || []).length, 2);
  assert.doesNotMatch(line.attrs.d, /L/);
  assert.equal(children.filter(x => x.tag === 'circle').length, 2);
  assert.equal(n['kpi-chart-scale'].textContent, 'Escala ampliada: 0–130%');
  n['kpi-chart-toggle'].onclick();
  assert.equal(n['kpi-chart-scale'].textContent, 'Escala completa: 0–120%');
});
