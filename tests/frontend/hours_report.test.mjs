import { test } from 'node:test';
import assert from 'node:assert/strict';

import { csvCell, hoursScale, monthCsv } from '../../frontend/static/scripts/lib/hours-report.js';

test('the scale rounds the tallest bar up to half a power of ten', () => {
  assert.deepEqual(hoursScale([{ total: 730, budget: 400 }]).ticks, [0, 187.5, 375, 562.5, 750]);
  assert.equal(hoursScale([{ total: 0 }]).top, 1);
  assert.equal(hoursScale([{ total: 10, budget: 1200 }]).top, 1500);
});

test('spreadsheet formulas are neutralised and quotes doubled', () => {
  assert.equal(csvCell('=SUM(A1)'), '"\'=SUM(A1)"');
  assert.equal(csvCell('-5'), '"\'-5"');
  assert.equal(csvCell('di "hola"'), '"di ""hola"""');
  assert.equal(csvCell(null), '""');
  assert.equal(csvCell(12.5), '"12.5"');
});

test('the month CSV has a BOM, a header and one line per project', () => {
  const csv = monthCsv({
    label: 'Oct 2026',
    projects: [{ id: 'P1', name: 'Portal', client: 'Acme', service: 'RaaS', project_budget: null, billable: 1, operational: 2, commercial: 3, total: 6 }],
  });
  const lines = csv.split('\r\n');
  assert.ok(lines[0].startsWith('﻿"ID"'));
  assert.equal(lines.length, 2);
  assert.equal(lines[1], '"P1","Portal","Acme","RaaS","","1","2","3","6"');
});
