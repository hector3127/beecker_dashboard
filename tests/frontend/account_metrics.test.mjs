import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  alerts,
  averageProgress,
  byService,
  hourTotals,
  npsAverage,
  pageOf,
  stageTone,
  stateCounts,
} from '../../frontend/static/scripts/lib/account-metrics.js';

const projects = [
  { id: 'A', service: 'ixb', stage: 'Completed', state: 'Producción', budget: 100, burn: 50, nps: 8 },
  { id: 'B', service: 'RaaS', stage: 'Build', state: 'En desarrollo', budget: 100, burn: 150, nps: 6 },
  { id: 'C', service: 'RaaS', stage: 'Build', state: 'En desarrollo', budget: 0, burn: 40, late: true },
  { id: 'D', service: null, stage: 'Build', state: null, budget: 10, burn: null, clockify_pending: true },
];

test('hours add up and a missing budget gives no ratio', () => {
  assert.deepEqual(hourTotals(projects.slice(0, 2)), { burn: 200, budget: 200, ratio: 100 });
  assert.equal(hourTotals([{ id: 'x', burn: 5 }]).ratio, null);
});

test('progress averages only projects with budget and hours already read', () => {
  assert.equal(averageProgress(projects), (50 + 150) / 2);
  assert.equal(averageProgress([projects[3]]), null);
});

test('services are grouped with IxB normalised and the split adds to 100', () => {
  const groups = byService(projects);
  assert.deepEqual(groups.map((g) => g.name), ['IxB', 'RaaS', 'Sin servicio']);
  const raas = groups[1];
  assert.equal(raas.count, 2);
  assert.equal(raas.risk, 100); // B excede y C esta vencido
  assert.equal(raas.completed + raas.risk + raas.other, 100);
});

test('states keep the order they first appear and a missing one is named', () => {
  assert.deepEqual(stateCounts(projects), [
    { name: 'Producción', count: 1, percent: 25 },
    { name: 'En desarrollo', count: 2, percent: 50 },
    { name: 'Sin estado', count: 1, percent: 25 },
  ]);
});

test('alerts say why: over budget wins over a late date', () => {
  assert.deepEqual(
    alerts(projects).map((a) => [a.project.id, a.reason]),
    [
      ['B', 'Consumo mayor que el presupuesto'],
      ['C', 'Fecha vencida'],
    ],
  );
});

test('NPS averages only rated projects', () => {
  assert.equal(npsAverage(projects), 7);
  assert.equal(npsAverage([projects[3]]), null);
});

test('stage colours follow the old rules', () => {
  assert.equal(stageTone('Completed'), 'green');
  assert.equal(stageTone('Cancelado'), 'red');
  assert.equal(stageTone('Suspendido'), 'yellow');
  assert.equal(stageTone(null), 'purple');
});

test('paging clamps the page and reports the visible range', () => {
  const items = Array.from({ length: 13 }, (_, i) => i);
  assert.deepEqual(pageOf(items, 3, 6), { items: [12], page: 3, pages: 3, from: 13, to: 13 });
  assert.equal(pageOf(items, 99, 6).page, 3);
  assert.deepEqual(pageOf([], 1, 6), { items: [], page: 1, pages: 1, from: 0, to: 0 });
});

test('the budget analysis ignores projects whose hours are not read yet', async () => {
  const { budgetView } = await import('../../frontend/static/scripts/lib/account-metrics.js');
  const view = budgetView(projects);
  assert.deepEqual(view.selected.map((p) => p.id), ['A', 'B', 'C']);
  assert.equal(view.exceeded, 1);
  assert.deepEqual(view.services.map((s) => [s.name, s.burn]), [['IxB', 50], ['RaaS', 190]]);
  assert.equal(Math.round(view.services[1].percent), 79);
});

test('the budget analysis filters by service and search, and can group by project', async () => {
  const { budgetView } = await import('../../frontend/static/scripts/lib/account-metrics.js');
  assert.deepEqual(budgetView(projects, { service: 'RaaS' }).selected.map((p) => p.id), ['B', 'C']);
  assert.deepEqual(budgetView(projects, { search: 'b' }).selected.map((p) => p.id), ['B']);
  assert.deepEqual(budgetView(projects, { by: 'project' }).groups.map((g) => g.name), ['A', 'B', 'C']);
});
