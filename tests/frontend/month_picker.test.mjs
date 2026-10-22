import { test } from 'node:test';
import assert from 'node:assert/strict';

import { monthIndex, monthValue, shiftMonth } from '../../frontend/static/scripts/ui/month-picker.js';

test('a month converts to an index and back', () => {
  for (const value of ['2024-08', '2026-10', '2027-01', '2025-12']) {
    assert.equal(monthValue(monthIndex(value)), value);
  }
  assert.equal(monthIndex('2026-10') - monthIndex('2026-09'), 1);
});

test('stepping crosses year boundaries', () => {
  assert.equal(shiftMonth('2026-01', -1, '2024-08', '2026-10'), '2025-12');
  assert.equal(shiftMonth('2025-12', 1, '2024-08', '2026-10'), '2026-01');
});

test('stepping never leaves the range', () => {
  assert.equal(shiftMonth('2024-08', -1, '2024-08', '2026-10'), '2024-08');
  assert.equal(shiftMonth('2026-10', 1, '2024-08', '2026-10'), '2026-10');
});

test('a month picked outside the range is clamped to the nearest limit', () => {
  assert.equal(shiftMonth('2027-03', 0, '2024-08', '2026-10'), '2026-10');
  assert.equal(shiftMonth('2023-01', 0, '2024-08', '2026-10'), '2024-08');
});
