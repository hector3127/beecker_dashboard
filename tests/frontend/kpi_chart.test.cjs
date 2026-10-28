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

test('the trend uses smooth curves through the same measured monthly points', async (t) => {
  const values = [100, 0, 100];
  const n = await harness(t, [{name: 'Ana', values}]);
  const children = n['kpi-chart'].children;
  const path = children.find(x => x.tag === 'path').attrs.d;
  assert.equal((path.match(/C/g) || []).length, 2);
  assert.doesNotMatch(path, /L/);
  assert.equal(children.filter(x => x.tag === 'circle').length, 3);
  assert.deepEqual(children.filter(x => x.tag === 'circle').map(x => Number(x.attrs.cx)), [45, 290, 535]);
  assert.deepEqual(values, [100, 0, 100]);
  assert.match(n['kpi-chart'].attrs['aria-label'], /Tendencia mensual de cumplimiento/);
});

test('smooth trend never overshoots zero, peaks, flat runs or their segment endpoints', async () => {
  const { trendSegments, trendPath } = await import('../../frontend/static/scripts/pages/kpis_dm/sections/trend_model.js');
  for (const values of [[100,100,0,100,100], [0,50,51,100], [100,0,0,50,0], [0,0,0], [100,100,100]]) {
    const points = values.map((y,x) => ({x,y}));
    const original = structuredClone(points);
    for (const {start,c1,c2,end} of trendSegments(points)) {
      for (let i=0;i<=100;i++) {
        const t=i/100, u=1-t;
        const y=u*u*u*start.y+3*u*u*t*c1.y+3*u*t*t*c2.y+t*t*t*end.y;
        assert.ok(y >= Math.min(start.y,end.y)-1e-9 && y <= Math.max(start.y,end.y)+1e-9);
      }
    }
    assert.deepEqual(points,original);
  }
  assert.equal(trendPath([]),'');
  assert.equal(trendPath([{x:0,y:50}]),'M0 50');
  const gap=trendPath([{x:0,y:100},{x:1,y:0},null,{x:3,y:50},{x:4,y:100}]);
  assert.equal((gap.match(/M/g)||[]).length,2);
  assert.equal((gap.match(/C/g)||[]).length,2);
});
