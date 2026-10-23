import { test } from 'node:test';
import assert from 'node:assert/strict';

const { range, cells, iso, date } = await import('../../frontend/static/scripts/lib/calendar.js');

test('quick ranges use local calendar dates across year and leap boundaries', () => {
  assert.deepEqual(range('lastmonth', new Date(2026, 0, 14)), ['2025-12-01', '2025-12-31']);
  assert.deepEqual(range('month', new Date(2024, 1, 14)), ['2024-02-01', '2024-02-29']);
  assert.deepEqual(range('quarter', new Date(2026, 9, 14)), ['2026-10-01', '2026-12-31']);
  assert.deepEqual(range('week', new Date(2026, 9, 14)), ['2026-10-12', '2026-10-18']);
  assert.deepEqual(range('seven', new Date(2026, 0, 3)), ['2025-12-28', '2026-01-03']);
  assert.deepEqual(range('yesterday', new Date(2026, 0, 1)), ['2025-12-31', '2025-12-31']);
  assert.deepEqual(range('year', new Date(2026, 5, 1)), ['2026-01-01', '2026-12-31']);
});

test('dual calendar grids begin on Monday and include adjacent months', () => {
  const grid = cells(2026, 6);
  assert.equal(grid.length, 42);
  assert.equal(grid[0].key, '2026-06-29');
  assert.equal(grid[0].outside, true);
  assert.equal(grid.find((d) => d.key === '2026-07-16').outside, false);
  assert.equal(grid.at(-1).key, '2026-08-09');
});

test('dates round-trip without a timezone shift', () => {
  assert.equal(iso(date('2026-03-08')), '2026-03-08');
  assert.equal(iso(date('2026-11-01')), '2026-11-01');
});
