import { test } from 'node:test';
import assert from 'node:assert/strict';

import { billingBars, donutArcs, percentText } from '../../frontend/static/scripts/lib/charts.js';

// Los valores esperados salen de las funciones de Python que dibujaban estas
// graficas (build_donut_segments y build_chart_bars); asi el trazo no cambia.
const near = (actual, expected, label) => assert.ok(Math.abs(actual - expected) <= 0.11, `${label}: ${actual} vs ${expected}`);

test('donut arcs match the server geometry', () => {
  const cases = [
    [[1, 0, 2], [[134.0, 268.1, 0], [0.0, 402.1, -134.0], [268.1, 134.0, -134.0]]],
    [[3, 2, 1], [[201.1, 201.1, 0], [134.0, 268.1, -201.1], [67.0, 335.1, -335.1]]],
    [[5, 0, 0], [[402.1, 0.0, 0], [0.0, 402.1, -402.1], [0.0, 402.1, -402.1]]],
    [[7, 3, 2], [[234.6, 167.6, 0], [100.5, 301.6, -234.6], [67.0, 335.1, -335.1]]],
    [[0, 0, 0], [[0.0, 402.1, 0], [0.0, 402.1, 0], [0.0, 402.1, 0]]],
  ];
  for (const [counts, expected] of cases) {
    donutArcs(counts).forEach((arc, i) => {
      near(arc.dash, expected[i][0], `dash ${counts}`);
      near(arc.gap, expected[i][1], `gap ${counts}`);
      near(arc.offset, expected[i][2], `offset ${counts}`);
    });
  }
});

test('an empty donut has no negative zero in its offsets', () => {
  assert.ok(donutArcs([1, 0, 2]).every((arc) => !Object.is(arc.offset, -0)));
});

test('billing bars match the server geometry', () => {
  const cases = [
    [[68.5, 70, null, 95.2, 120], [[44.6, 46.6, 40, 53.4, 64.6, 40.6], [145.8, 45.4, 40, 54.6, 165.8, 39.4], [247.0, 100.0, 40, 0, 267.0, 94.0], [348.2, 25.7, 40, 74.3, 368.2, 19.7], [449.4, 10.3, 40, 89.7, 469.4, 4.3]]],
    [[50], [[247.0, 61.0, 40, 39.0, 267.0, 55.0]]],
    [[null, null], [[120.5, 100.0, 40, 0, 140.5, 94.0], [373.5, 100.0, 40, 0, 393.5, 94.0]]],
    [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100], [[21.4, 92.2, 35.9, 7.8, 39.3, 86.2], [476.8, 22.0, 35.9, 78.0, 494.8, 16.0]]],
  ];
  for (const [percents, expected] of cases) {
    const bars = billingBars(percents);
    assert.equal(bars.length, percents.length);
    const picks = expected.length === percents.length ? bars : [bars[0], bars.at(-1)];
    picks.forEach((bar, i) => {
      const [x, y, width, height, center, textY] = expected[i];
      near(bar.x, x, 'x');
      near(bar.y, y, 'y');
      near(bar.width, width, 'width');
      near(bar.height, height, 'height');
      near(bar.center, center, 'center');
      near(bar.textY, textY, 'textY');
    });
  }
});

test('no months means no bars', () => {
  assert.deepEqual(billingBars([]), []);
});

test('percent text keeps integers whole and one decimal otherwise', () => {
  assert.equal(percentText(68.5), '68.5%');
  assert.equal(percentText(70), '70%');
  assert.equal(percentText(120), '120%');
  assert.equal(percentText(95.24), '95.2%');
  assert.equal(percentText(null), '—');
  assert.equal(percentText(undefined), '—');
});
