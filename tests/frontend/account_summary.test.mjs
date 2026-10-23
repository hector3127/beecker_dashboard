import { test } from 'node:test';
import assert from 'node:assert/strict';

const { averageProgress, isAlert, roundHalfEven, serviceHours, serviceModels, serviceName, stateSlices } = await import(
  '../../frontend/static/scripts/lib/account-summary.js'
);

const project = (extra) => ({ id: 'P', service: 'T&M', stage: 'Build', state: 'En desarrollo', budget: 100, burn: 50, ...extra });

test('rounding goes to the nearest even number like the server', () => {
  assert.equal(roundHalfEven(12.5), 12);
  assert.equal(roundHalfEven(13.5), 14);
  assert.equal(roundHalfEven(66.7), 67);
});

test('the average progress ignores pending, unbudgeted and unknown projects', () => {
  const projects = [
    project({ burn: 50 }),
    project({ burn: 150 }),
    project({ burn: 10, clockify_pending: true }),
    project({ budget: 0 }),
    project({ burn: null }),
  ];
  assert.equal(averageProgress(projects), 100);
  assert.equal(averageProgress([project({ burn: null })]), null);
});

test('service models split completed, other and alerted projects', () => {
  const rows = serviceModels([
    project({ stage: 'Completed' }),
    project({ stage: 'Completado', exceeded: true }),
    project({ stage: 'Build' }),
    project({ stage: 'Build', late: true, service: null }),
  ]);
  const tm = rows.find((row) => row.name === 'T&M');
  assert.deepEqual([tm.count, tm.completed, tm.risk, tm.other], [3, 33, 33, 34]);
  assert.equal(rows.find((row) => row.name === 'Sin servicio').risk, 100);
});

test('state slices accumulate the offset and cycle the colors', () => {
  const slices = stateSlices([project({}), project({}), project({ state: 'Pausado' }), project({ state: '' })]);
  assert.deepEqual(slices.map((s) => [s.name, s.count, s.percent]), [['En desarrollo', 2, 50], ['Pausado', 1, 25], ['Sin estado', 1, 25]]);
  assert.equal(slices[1].offset, -50);
  assert.equal(slices[2].offset, -75);
});

test('IxB is one service whatever its case and hours add by service', () => {
  assert.equal(serviceName({ service: 'ixb' }), 'IxB');
  assert.equal(serviceName({ service: null }), 'Sin servicio');
  const hours = serviceHours([project({ service: 'ixb' }), project({ service: 'IXB', burn: null })]);
  assert.deepEqual(hours.get('IxB'), { budget: 200, burn: 50 });
  assert.equal(isAlert(project({ late: true })), true);
});
