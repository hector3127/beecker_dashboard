import { test } from 'node:test';
import assert from 'node:assert/strict';

import { monthlyModel } from '../../frontend/static/scripts/lib/monthly-model.js';

const row = (i, extra = {}) => ({ month: `2026-0${i}`, revenue: 100, cost: 50, margin: 50, ...extra });

test('six months fit a narrow card without a forced desktop width', () => {
  const data = { months: Array.from({ length: 6 }, (_, i) => row(i + 1)) };
  assert.equal(monthlyModel(data, 300).width, 300);
  assert.equal(monthlyModel(data, 250).width, 250);
  assert.equal(monthlyModel(data, 100).width, 240);
  const model = monthlyModel(data, 300);
  assert.equal(model.columns.length, 6);
  assert.doesNotMatch(JSON.stringify(model), /NaN|Infinity|null,"y"/);
});

test('a missing cost stays pending, a missing margin splits the line, negatives stay visible', () => {
  const model = monthlyModel({ months: [row(1, { cost: 120, margin: -20 }), row(2, { cost: null, margin: null }), row(3, { revenue: -20, cost: 0, margin: 150 })] }, 900);
  assert.equal(model.columns[1].cost, null);
  assert.equal(model.segments.length, 2);
  assert.equal(model.columns[2].revenue.value, -20);
  assert.ok(model.columns[2].revenue.height > 0);
});

test('long ranges widen the chart and empty ranges stay empty', () => {
  const months = Array.from({ length: 24 }, () => row(1));
  assert.ok(monthlyModel({ months }, 900).width >= 120 + 24 * 84);
  const empty = monthlyModel({ months: [] }, 900);
  assert.equal(empty.columns.length, 0);
  assert.equal(empty.rightTicks.length, 0);
});
