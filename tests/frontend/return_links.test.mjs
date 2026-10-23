import { test } from 'node:test';
import assert from 'node:assert/strict';

const { withReturn } = await import('../../frontend/static/scripts/ui/return-links.js');
const at = (path) => new URL(path, 'http://localhost:8000');

test('an account link carries the current screen as the way back', () => {
  const next = withReturn(at('/cuenta/acme/?nombre=ACME'), at('/ejecutiva/oportunidades/?nombre=ACME'));
  const url = new URL(next);
  assert.equal(url.searchParams.get('volver'), '/ejecutiva/oportunidades/?nombre=ACME');
  assert.equal(url.searchParams.get('nombre'), 'ACME');
});

test('the chosen period travels with the link unless it already has one', () => {
  const source = at('/ejecutiva/oportunidades/?periodo=mes&anio=2026&mes=3');
  const url = new URL(withReturn(at('/ejecutiva/costos/detalle/'), source));
  assert.equal(url.searchParams.get('periodo'), 'mes');
  assert.equal(url.searchParams.get('mes'), '3');
  const own = new URL(withReturn(at('/ejecutiva/costos/detalle/?periodo=anio&anio=2025'), source));
  assert.equal(own.searchParams.get('periodo'), 'anio');
  assert.equal(own.searchParams.get('anio'), '2025');
});

test('links to other screens or other sites are left alone', () => {
  assert.equal(withReturn(at('/operativa/'), at('/operativa/eva-4/')), null);
  assert.equal(withReturn(new URL('https://otro.example/cuenta/x/'), at('/operativa/')), null);
});
