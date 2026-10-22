import { test } from 'node:test';
import assert from 'node:assert/strict';

import { withReturn } from '../../frontend/static/scripts/data/navigation.js';

const here = (search) => ({ origin: 'http://x.test', pathname: '/ejecutiva/oportunidades/', search, hash: '' });

test('the detail link carries the current page and the chosen period', () => {
  const link = withReturn('/ejecutiva/costos/detalle/?vista=proyectos', here('?periodo=mes&anio=2026&mes=3&nombre=Acme'));
  const url = new URL(link, 'http://x.test');
  assert.equal(url.searchParams.get('periodo'), 'mes');
  assert.equal(url.searchParams.get('mes'), '3');
  assert.equal(url.searchParams.get('vista'), 'proyectos');
  assert.equal(url.searchParams.get('volver'), '/ejecutiva/oportunidades/?periodo=mes&anio=2026&mes=3&nombre=Acme');
});

test('a period already on the link is not overwritten', () => {
  const link = withReturn('/cuenta/a/?periodo=anio&anio=2025', here('?periodo=mes&mes=3'));
  assert.equal(new URL(link, 'http://x.test').searchParams.get('periodo'), 'anio');
});

test('without a period the page is still remembered, and other origins are untouched', () => {
  assert.match(withReturn('/cuenta/a/', here('')), /volver=%2Fejecutiva%2Foportunidades%2F$/);
  assert.equal(withReturn('https://otro.test/x', here('')), 'https://otro.test/x');
});
