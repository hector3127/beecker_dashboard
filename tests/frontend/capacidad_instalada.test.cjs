const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../apps/portal/static/portal/js/capacidad_instalada.js'), 'utf8');

function harness() {
  const nodes = new Map(), requests = [], blobs = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {style: {}, value: '', innerHTML: '', textContent: '',
      classList: {toggle() {}}, setAttribute() {}, appendChild(child) {nodes.set(child.id, child);}, click() {}});
    return nodes.get(id);
  }
  function runner(success, failure) {
    return {withSuccessHandler(fn) {return runner(fn, failure);},
      withFailureHandler(fn) {return runner(success, fn);},
      capacidadInstaladaBase(...args) {requests.push({kind: 'base', args, success, failure});},
      capacidadInstaladaDatosProyecto(...args) {requests.push({kind: 'project', args, success, failure});}};
  }
  const context = {document: {getElementById: id => id === 'ci-panel' ? nodes.get(id) : node(id),
    createElement: () => node('created')},
    location: {search: '?mes=2026-10'}, URLSearchParams, Blob,
    URL: {createObjectURL(blob) {blobs.push(blob); return 'blob:test';}, revokeObjectURL() {}},
    setTimeout: () => {}, google: {script: {run: runner()}}};
  context.window = context;
  vm.runInNewContext(source, context);
  return {context, node, requests, blobs};
}

function complete(h) {
  h.requests[0].success({ok: true, mes: '2026-10', bandaColumna: 'Octubre', fuentes: ['Recursos'],
    filas: [{recurso: 'Ana', idProyecto: 'P1', iteration: '', concepto: 'Proyecto', banda: 'B1', tecnologia: 'Dev',
      regla: {afecta: true, facturable: 'Facturable', cargabilidad: 'Cargable'}}]});
  h.requests[1].success({ok: true, inicio: '2026-10-01', fin: '2026-10-31', daily: {ana: {'2026-10-01': 10}}});
}

test('capacity opens and calculates the selected month without legacy hosts or GSE', () => {
  const h = harness();
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].args[0], '2026-10');
  assert.match(h.node('ci-panel').innerHTML, /<h1>Capacidad instalada/);
  assert.doesNotMatch(h.node('ci-panel').innerHTML, /Cerrar capacidad|gseAbrir|ciCerrar/);
  complete(h);
  assert.match(h.node('ci-content').innerHTML, /176 h/);
  assert.match(h.node('ci-content').innerHTML, /168 h/);
  assert.match(h.node('ci-content').innerHTML, /10 h/);
  assert.match(h.node('ci-content').innerHTML, /Ana/);
  h.context.ciVista('people');
  assert.match(h.node('ci-content').innerHTML, /ci-resource-grid/);
  h.context.ciJornada(6);
  assert.match(h.node('ci-content').innerHTML, /132 h/);
});

test('filters, CSV and forced refresh keep working on the standalone page', async () => {
  const h = harness(); complete(h);
  h.context.ciExportar();
  const csv = await h.blobs[0].text();
  assert.match(csv, /Ana/);
  assert.match(csv, /P1/);
  assert.match(csv, /01\/10\/2026/);
  h.context.ciFiltro('q', 'Sin coincidencia');
  assert.doesNotMatch(h.node('ci-content').innerHTML, /<b>Ana<\/b>/);
  h.context.ciRefrescar();
  h.requests[2].success({ok: true, mes: '2026-10', fuentes: [], filas: [
    {recurso: 'Ana', idProyecto: 'P1', iteration: '', concepto: 'Proyecto', regla: {afecta: true}},
  ]});
  assert.equal(h.requests[3].args[3], true);
});
