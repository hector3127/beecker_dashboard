import { test } from 'node:test';
import assert from 'node:assert/strict';

const { monthlyChartModel } = await import('../../frontend/static/scripts/lib/monthly-chart.js');

const count = (model, tag) => model.items.filter((item) => item.tag === tag).length;
const texts = (model) => model.items.filter((item) => item.tag === 'text').map((item) => item.text);

test('six months fit a narrow card without a forced desktop width', () => {
  const data = { months: Array.from({ length: 6 }, (_, i) => ({ month: `2026-0${i + 1}`, revenue: 100, cost: 50, margin: 50 })) };
  const model = monthlyChartModel(data, 300);
  assert.equal(model.width, 300);
  assert.equal(count(model, 'rect'), 12);
  assert.equal(monthlyChartModel(data, 250).width, 250);
  assert.ok(!JSON.stringify(model).includes('NaN') && !JSON.stringify(model).includes('Infinity'));
});

test('missing costs stay pending, missing margins split the line and negative values remain visible', () => {
  const data = {
    months: [
      { month: '2026-01', revenue: 100, cost: 120, margin: -20 },
      { month: '2026-02', revenue: 100, cost: null, margin: null },
      { month: '2026-03', revenue: -20, cost: 0, margin: 150 },
    ],
  };
  const model = monthlyChartModel(data, 900);
  assert.ok(texts(model).includes('Pendiente'));
  assert.equal(count(model, 'polyline'), 2);
  const titles = model.items.map((item) => item.title).filter(Boolean).join('|');
  assert.match(titles, /-20/);
  assert.match(titles, /150/);
  assert.ok(!JSON.stringify(model).includes('NaN'));
});

test('long ranges retain readable spacing and empty ranges explain their state', () => {
  const months = Array.from({ length: 24 }, () => ({ month: '2026-01', revenue: 1, cost: 0, margin: 100 }));
  assert.equal(monthlyChartModel({ months }, 320).width, 2136);
  assert.ok(texts(monthlyChartModel({ months: [] }, 320)).includes('Sin datos para este periodo'));
});

test('wide charts show margin labels and mark partial values explicitly', () => {
  const months = [{ month: '2026-01', revenue: 100, cost: 25, margin: 75 }];
  assert.ok(texts(monthlyChartModel({ months, complete: true }, 900)).includes('75%'));
  assert.ok(texts(monthlyChartModel({ months, complete: false }, 900)).includes('75%*'));
});


test('annual data fits desktop and keeps twelve labels including future gaps', () => {
  const months = Array.from({length: 12}, (_, i) => ({month: `2026-${String(i + 1).padStart(2, '0')}`, revenue: i < 10 ? 100 : null, cost: i < 10 ? 50 : null, margin: i < 10 ? 50 : null, future: i >= 10}));
  const model = monthlyChartModel({months}, 980);
  assert.equal(model.width, 980);
  for (const month of ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']) assert.ok(texts(model).includes(month));
  assert.equal(texts(model).filter(x => x === 'Futuro').length, 2);
  assert.equal(count(model, 'rect'), 20);
  assert.ok(monthlyChartModel({months}, 320).width > 320);
});
