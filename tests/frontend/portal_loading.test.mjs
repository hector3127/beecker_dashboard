import { test } from 'node:test';
import assert from 'node:assert/strict';

const { isLoadingMessage } = await import('../../frontend/static/scripts/ui/portal-loading.js');

test('only real loading texts are loading messages', () => {
  for (const text of ['Cargando datos', 'Consultando…', ' calculando capacidad', 'Preparando: espera', 'Actualizando']) {
    assert.equal(isLoadingMessage(text), true, text);
  }
  for (const text of ['Pendiente', 'No disponible', 'Consultas hechas', '', null, 'Cargando '.padEnd(230, 'x')]) {
    assert.equal(isLoadingMessage(text), false, String(text));
  }
});
