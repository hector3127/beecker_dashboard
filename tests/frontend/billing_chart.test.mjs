import { test } from 'node:test';
import assert from 'node:assert/strict';

import { describeMonth } from '../../frontend/static/scripts/ui/billing-chart.js';
import { meterPercent } from '../../frontend/static/scripts/pages/operativa/sections/capacity.js';

const context = { target: 70, latestMonth: '2026-09', monthClosed: true };
const month = (extra) => ({ month: '2026-09', label: 'Sep', month_label: 'Septiembre 2026', global_percent: 68.5, fixed_percent: 12.4, variable_percent: 56.1, ...extra });

test('a month below the target says how far it is', () => {
  const view = describeMonth(month(), context);
  assert.equal(view.value, '68.5%');
  assert.equal(view.gap, -1.5);
  assert.equal(view.gapText, '↓ 1.5 puntos abajo de la meta');
  assert.equal(view.fixed, 'AER 12%');
  assert.equal(view.variable, 'PRJ 56%');
});

test('a month above the target', () => {
  const view = describeMonth(month({ global_percent: 75.25 }), context);
  assert.equal(view.gap, 5.25);
  assert.equal(view.gapText, '↑ 5.3 puntos arriba de la meta');
});

test('a month without data says there is nothing to compare', () => {
  const view = describeMonth(month({ global_percent: null, fixed_percent: null, variable_percent: null }), context);
  assert.equal(view.value, '—');
  assert.equal(view.gap, null);
  assert.equal(view.gapText, 'Sin datos para comparar con la meta');
  assert.equal(view.fixed, 'AER —');
});

test('the label tells if the month is the latest, closed or running, or a selection', () => {
  assert.equal(describeMonth(month(), context).label, 'Septiembre 2026 · último mes cerrado');
  assert.equal(describeMonth(month(), { ...context, monthClosed: false }).label, 'Septiembre 2026 · mes en curso');
  assert.equal(describeMonth(month({ month: '2026-03', month_label: 'Marzo 2026' }), context).label, 'Marzo 2026 · mes seleccionado');
});

test('the capacity meter stays between 0 and 100 and survives a zero base', () => {
  assert.equal(meterPercent(64, 160), 40);
  assert.equal(meterPercent(200, 160), 100);
  assert.equal(meterPercent(-5, 160), 0);
  assert.equal(meterPercent(10, 0), 0);
});
