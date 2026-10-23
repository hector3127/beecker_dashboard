import { test } from 'node:test';
import assert from 'node:assert/strict';

import { formatDate, formatDateTime, formatNumber, plain } from '../../frontend/static/scripts/lib/format.js';

test('numbers show up to two decimals and group thousands like the old pages', () => {
  assert.equal(formatNumber(12), '12');
  assert.equal(formatNumber(12.5), '12.5');
  assert.equal(formatNumber(1284.5), '1,284.5');
  assert.equal(formatNumber(1234567.891), '1,234,567.89');
  assert.equal(formatNumber(0), '0');
  assert.equal(formatNumber(-12), '-12');
});

test('dates become dd/mm/yyyy and anything else is empty', () => {
  assert.equal(formatDate('2026-10-20'), '20/10/2026');
  assert.equal(formatDate('2026-10-20T13:00:00'), '20/10/2026');
  for (const bad of [null, undefined, '', 'mañana', '20/10/2026']) assert.equal(formatDate(bad), '');
});

test('date and time keep the server wall clock, whatever the browser timezone', () => {
  const before = process.env.TZ;
  for (const zone of ['UTC', 'Asia/Tokyo']) {
    process.env.TZ = zone;
    assert.equal(formatDateTime('2026-10-22T09:35:12.123456-06:00'), '22/10/2026 09:35');
  }
  process.env.TZ = before;
  assert.equal(formatDateTime('2026-10-22'), '');
  assert.equal(formatDateTime(null), '');
});

test('search text ignores accents and case', () => {
  assert.equal(plain('Nestlé ÁÉÍÓÚ ñ'), 'nestle aeiou n');
  assert.ok(plain('Conciliación Mensual').includes(plain('CONCILIACION')));
});

test('money is compact, truncated and never zero when it is missing', async () => {
  const { formatMoney } = await import('../../frontend/static/scripts/lib/format.js');
  assert.equal(formatMoney(0), '$0');
  assert.equal(formatMoney(999), '$999');
  assert.equal(formatMoney(1500), '$1K');
  assert.equal(formatMoney(2_599_999), '$2.59M');
  assert.equal(formatMoney(1.2e9), '$1.2B');
  assert.equal(formatMoney(-1500), '-$1K');
  for (const missing of [null, undefined, Number.NaN]) assert.equal(formatMoney(missing), 'Pendiente');
});

test('percentages keep two decimals and a missing value stays pending', async () => {
  const { formatPercent } = await import('../../frontend/static/scripts/lib/format.js');
  assert.equal(formatPercent(40), '40.00%');
  assert.equal(formatPercent(-5, ' pp'), '-5.00 pp');
  assert.equal(formatPercent(null), 'Pendiente');
});

test('the compact figure has no currency symbol and shares the rules of money', async () => {
  const { formatCompact } = await import('../../frontend/static/scripts/lib/format.js');
  assert.equal(formatCompact(1_897_644.14), '1.89M');
  assert.equal(formatCompact(-1500), '-1K');
  assert.equal(formatCompact(null), 'Pendiente');
});

test('amounts that the API sends as decimal text are formatted, never pending', async () => {
  const { formatCompact, formatMoney } = await import('../../frontend/static/scripts/lib/format.js');
  assert.equal(formatCompact('1950326.71'), '1.95M');
  assert.equal(formatMoney('415926.17'), '$415K');
  assert.equal(formatMoney('-1500'), '-$1K');
  assert.equal(formatCompact(''), 'Pendiente');
  assert.equal(formatCompact('abc'), 'Pendiente');
});
