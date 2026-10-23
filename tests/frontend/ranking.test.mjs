import { test } from 'node:test';
import assert from 'node:assert/strict';

const { rankAccounts } = await import('../../frontend/static/scripts/lib/ranking.js');
const accounts = [
  { name: 'Grande', revenue: 1000, gross_profit: 100, margin: 10, pending: 2 },
  { name: 'Pequeña', revenue: 100, gross_profit: 90, margin: 90 },
  { name: 'Sin facturación', revenue: 0, gross_profit: -20, margin: null },
  { name: 'Heineken México', revenue: 500, gross_profit: 200, margin: 40 },
];

test('criterion changes the actual groups using the full cut', () => {
  const byProfit = rankAccounts(accounts, 'gross_profit');
  const byRevenue = rankAccounts(accounts, 'revenue');
  const byMargin = rankAccounts(accounts, 'margin');
  assert.equal(byProfit.healthy.rows[0].name, 'Heineken México');
  assert.equal(byRevenue.healthy.rows[0].name, 'Grande');
  assert.equal(byMargin.healthy.rows[0].name, 'Pequeña');
  assert.equal(byProfit.unhealthy.rows[0].gross_profit, -20);
  assert.equal(byMargin.missing, 1);
  assert.equal(byMargin.eligible, 3);
});

test('search ignores accents and includes a partial account without inventing zero margins', () => {
  const filtered = rankAccounts(accounts, 'gross_profit', 'mexico');
  assert.equal(filtered.healthy.rows[0].name, 'Heineken México');
  assert.equal(filtered.matched, 1);
  assert.equal(rankAccounts(accounts, 'gross_profit', 'grande').healthy.rows[0].pending, 2);
  assert.equal(rankAccounts(accounts, 'margin', 'sin facturacion').healthy.rows.length, 0);
});

test('sorting does not mutate source or duplicate accounts between groups', () => {
  const original = JSON.stringify(accounts);
  const result = rankAccounts(accounts, 'gross_profit', '', { healthy: 'ascending', unhealthy: 'descending' });
  assert.equal(result.healthy.rows[0].name, 'Grande');
  assert.equal(JSON.stringify(accounts), original);
  const names = [...result.healthy.rows, ...result.unhealthy.rows].map((row) => row.name);
  assert.equal(new Set(names).size, names.length);
});

test('groups are capped at five after comparing all accounts; empty data stays empty', () => {
  const data = Array.from({ length: 18 }, (_, i) => ({ name: `Cuenta ${i}`, revenue: i }));
  const result = rankAccounts(data, 'revenue');
  assert.equal(result.healthy.count, 9);
  assert.equal(result.healthy.rows.length, 5);
  assert.equal(result.healthy.rows[0].revenue, 17);
  assert.equal(result.unhealthy.rows[0].revenue, 0);
  assert.equal(rankAccounts([], 'gross_profit').eligible, 0);
});
