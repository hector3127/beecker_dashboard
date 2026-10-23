const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const main = '<script>' + fs.readFileSync(path.join(__dirname, '../../apps/portal/static/portal/js/proyecto_detalle.js'), 'utf8') + '</script>'; 
const capacity = fs.readFileSync(path.join(__dirname, '../../templates/legacy/GSE.html'), 'utf8');
// Isolated functions now call these real transport helpers; keep RPC assertions.
const projectReads = ['readProjectFilters', 'readProjectDashboard'].map(name =>
  main.match(new RegExp('function ' + name + '\\([^]*?\\n  \\}'))[0]
).join('\n');
const init = projectReads + '\n' + main.match(/function initDashboard\(\) \{[\s\S]*?\n  \}/)[0];

test('entering the old panel makes no executive or filters RPC requests', () => {
  vm.runInNewContext(init + '\ninitDashboard();', {
    URLSearchParams, projectParams: () => new URLSearchParams(''),
    window: {location: {search: ''}},
    document: {getElementById() {throw Error('Unexpected executive initialization');}},
  });
});

test('direct project and account links still initialize their filters', () => {
  for (const search of ['?proyecto=AIN.002%20CR', '?cuenta=Nestle']) {
    const requests = [];
    const runner = {withSuccessHandler() {return this;}, withFailureHandler() {return this;},
      getFiltrosDisponibles() {requests.push('filters');}};
    vm.runInNewContext(init + '\ninitDashboard();', {
      URLSearchParams, projectParams: () => new URLSearchParams(search), window: {location: {search}},
      document: {getElementById: () => null},
      google: {script: {run: runner}},
    });
    assert.deepEqual(requests, ['filters']);
  }
});

test('old navigation keeps GSE after capacity moves to its own page', () => {
  assert.match(capacity, /onclick="gseAbrir\(\)"/);
  assert.doesNotMatch(capacity, /onclick="ciAbrir\(\)"/);
  assert.doesNotMatch(capacity, /capacidadInstaladaBase\(/);
  assert.match(capacity, /location.replace\("\/capacidad-instalada\/"/);
  new vm.Script(main.slice(main.indexOf('<script>') + 8, main.lastIndexOf('</script>')));
});

test('a TYM direct link uses the AER/T&M endpoint even without filter metadata', () => {
  const classify = main.match(/function _esProyectoAERTYM\(idProyecto\) \{[\s\S]*?\n  \}/)[0];
  const load = main.match(/function loadDashboard\(\) \{[\s\S]*?\n  \}/)[0];
  const detail = {style: {}, innerHTML: ''};
  const nodes = {
    'f-proyecto': {value: 'TYM.AAU.001', selectedOptions: [{textContent: 'TYM.AAU.001'}]},
    'f-cliente': {value: 'Todos los clientes'},
    'dashboard-general': {style: {}},
    'dashboard-proyecto-detalle': detail,
  };
  const requests = [];
  const runner = {withSuccessHandler() {return this;}, withFailureHandler() {return this;},
    getDashboardAERTYMProyecto(id) {requests.push(id);},
    getDashboardEjecutivoProyecto() {throw Error('Wrong Proyectos endpoint');}};
  vm.runInNewContext(projectReads + '\n' + classify + '\n' + load + '\nloadDashboard();', {
    window: {},
    mapaMetaProyectosDashboard: {}, dashboardRequestSeq: 0,
    _clienteSeleccionadoDashboard: () => false,
    document: {getElementById: id => nodes[id] || null, body: {classList: {toggle() {}}}},
    google: {script: {run: runner}},
  });
  assert.deepEqual(requests, ['TYM.AAU.001']);
  assert.match(detail.innerHTML, /legacy-project-head/);
  assert.match(detail.innerHTML, /Consultando/);
  assert.doesNotMatch(detail.innerHTML, /<select/);
});

test('the full project engine boots from a portal URL with its ID in JSON', () => {
  for (const [id, service, expected] of [
    ['AMK.004_CR', 'IXB', 'executive'], ['TYM.AAU.001', 'TYM', 'aer'],
  ]) {
    const nodes = {
      'project-context': {textContent: JSON.stringify({id})},
      'view-container': {innerHTML: '', appendChild() {}},
      'tpl-dashboard': {content: {cloneNode: () => ({})}},
      'btn-refresh': {},
      'f-proyecto': {value: id, options: [{value: id}], selectedOptions: [{textContent: id}]},
      'f-cliente': {value: 'Todos los clientes', options: [{value: 'Todos los clientes'}]},
      'dashboard-general': {style: {}},
      'dashboard-proyecto-detalle': {style: {}, innerHTML: ''},
    };
    const requests = [];
    function runner(success) {
      return {withSuccessHandler(fn) {return runner(fn);}, withFailureHandler() {return this;},
        getFiltrosDisponibles() {requests.push({kind: 'filters', success});},
        getDashboardEjecutivoProyecto(pid) {requests.push({kind: 'executive', pid});},
        getDashboardAERTYMProyecto(pid) {requests.push({kind: 'aer', pid});}};
    }
    const context = {
      URLSearchParams, location: {search: ''}, setTimeout() {},
      addEventListener() {},
      document: {readyState: 'loading', getElementById: id => nodes[id] || null,
        querySelector: () => null, querySelectorAll: () => [], addEventListener() {},
        body: {classList: {remove() {}, toggle() {}}}},
      google: {script: {run: runner()}},
    };
    context.window = context;
    vm.runInNewContext(main.slice(8, -9), context);
    assert.equal(requests[0].kind, 'filters');
    requests[0].success({proyectos: [{id, nombre: 'Proyecto', servicio: service}], clientes: ['Todos los clientes']});
    assert.equal(requests[1].kind, expected);
    assert.equal(requests[1].pid, id);
    assert.match(nodes['dashboard-proyecto-detalle'].innerHTML, /legacy-project-head/);
  }
});
