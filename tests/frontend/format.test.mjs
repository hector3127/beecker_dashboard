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
