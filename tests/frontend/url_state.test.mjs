import { test } from 'node:test';
import assert from 'node:assert/strict';

import { withParams, readParams } from '../../frontend/static/scripts/data/url-state.js';

test('adds and replaces parameters and keeps the rest of the URL', () => {
  const href = '/operativa/eva-4/?mes=2026-09&buscar=ana#tabla';
  assert.equal(withParams(href, { mes: '2026-10', servicio: 'RAAS' }), '/operativa/eva-4/?mes=2026-10&buscar=ana&servicio=RAAS#tabla');
});

test('empty values remove the parameter', () => {
  assert.equal(withParams('/x/?a=1&b=2&c=3', { a: '', b: null, c: undefined }), '/x/');
});

test('numbers are written as text, zero included', () => {
  assert.equal(withParams('/x/', { pagina: 0 }), '/x/?pagina=0');
});

test('values are encoded', () => {
  assert.equal(withParams('/x/', { cuenta: 'T&M ñ' }), '/x/?cuenta=T%26M+%C3%B1');
});

test('readParams parses a query string', () => {
  assert.equal(readParams('?mes=2026-10').get('mes'), '2026-10');
});
