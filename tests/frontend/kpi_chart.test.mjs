import { test } from 'node:test';
import assert from 'node:assert/strict';

import { chartScale, seriesPath } from '../../frontend/static/scripts/lib/kpi-chart.js';

test('the zoomed scale hugs the values and the full scale is at least 0-100', () => {
  const zoom = chartScale([62, 71, null, 80], false);
  assert.deepEqual([zoom.minimum, zoom.maximum], [50, 90]);
  assert.equal(zoom.ticks.at(-1), zoom.maximum);
  const full = chartScale([62, 71, 80], true);
  assert.deepEqual(full.ticks, [0, 25, 50, 75, 100]);
  assert.equal(chartScale([140], true).maximum, 140);
});

test('no values still gives a drawable scale and says there are none', () => {
  const empty = chartScale([null, null], false);
  assert.equal(empty.hasValues, false);
  assert.ok(empty.maximum > empty.minimum);
});

test('a missing value breaks the line instead of drawing through it', () => {
  const x = (i) => i * 10;
  const y = (v) => 100 - v;
  assert.equal(seriesPath([10, 20, null, 30, 40], x, y), 'M0 90L10 80M30 70L40 60');
  assert.equal(seriesPath([null], x, y), '');
});
