import { test } from 'node:test';
import assert from 'node:assert/strict';

import { rankAccounts } from '../../frontend/static/scripts/lib/ranking.js';

const accounts = [
  { name: 'Grande', revenue: 1000, gross_profit: 100, margin: 10, partial: true },
  { name: 'Pequeña', revenue: 100, gross_profit: 90, margin: 90 },
  { name: 'Sin facturación', revenue: 0, gross_profit: -20, margin: null },
  { name: 'Heineken México', revenue: 500, gross_profit: 200, margin: 40 },
];

test('the criterion changes the actual groups using the full cut', () => {
  assert.equal(rankAccounts(accounts, 'gross_profit').top.rows[0].name, 'Heineken México');
  assert.equal(rankAccounts(accounts, 'revenue').top.rows[0].name, 'Grande');
  const byMargin = rankAccounts(accounts, 'margin');
  assert.equal(byMargin.top.rows[0].name, 'Pequeña');
  assert.equal(byMargin.missing, 1);
  assert.equal(byMargin.eligible, 3);
  assert.equal(rankAccounts(accounts, 'gross_profit').bottom.rows[0].gross_profit, -20);
});

test('search ignores accents and a missing margin is never invented as zero', () => {
  const filtered = rankAccounts(accounts, 'gross_profit', 'mexico');
  assert.equal(filtered.top.rows[0].name, 'Heineken México');
  assert.equal(filtered.matched, 1);
  assert.equal(rankAccounts(accounts, 'margin', 'sin facturacion').top.rows.length, 0);
  assert.equal(rankAccounts(accounts, 'gross_profit', 'grande').partial, 1);
});

test('sorting neither mutates the source nor repeats an account between groups', () => {
  const original = JSON.stringify(accounts);
  const result = rankAccounts(accounts, 'gross_profit', '', { top: 'ascending', bottom: 'descending' });
  assert.equal(result.top.rows[0].name, 'Grande');
  assert.equal(JSON.stringify(accounts), original);
  const names = [...result.top.rows, ...result.bottom.rows].map((row) => row.name);
  assert.equal(new Set(names).size, names.length);
});

test('groups are capped at five after comparing every account; an unknown criterion falls back', () => {
  const data = Array.from({ length: 18 }, (_, i) => ({ name: `Cuenta ${i}`, revenue: i }));
  const result = rankAccounts(data, 'revenue');
  assert.equal(result.top.count, 9);
  assert.equal(result.top.rows.length, 5);
  assert.equal(result.top.rows[0].revenue, 17);
  assert.equal(result.bottom.rows[0].revenue, 0);
  assert.equal(rankAccounts([], 'gross_profit').eligible, 0);
  assert.equal(rankAccounts(accounts, 'otro').criterion, 'gross_profit');
});
