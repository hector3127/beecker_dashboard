import { test } from 'node:test';
import assert from 'node:assert/strict';
import { captureScale, captureName } from '../../frontend/static/scripts/ui/page-capture.js';

test('capture filenames retain primary names and sanitize other screen titles', () => {
  assert.equal(captureName('/', 'Otro título'), 'business-overview');
  assert.equal(captureName('/operativa/', 'Operativo'), 'operativa');
  assert.equal(captureName('/comercial/', 'Ventas'), 'comercial');
  assert.equal(captureName('/cuenta/heineken/', 'Cuenta Heineken México'), 'cuenta-heineken-mexico');
  assert.equal(captureName('/proyectos/AMK.008/', 'AMK.008 · Proyecto'), 'amk-008-proyecto');
  assert.equal(captureName('', ''), 'dashboard');
});

test('large pages stay within canvas side and pixel limits', () => {
  for (const [width, height] of [[1400, 900], [1400, 50000], [40000, 2000], [0, 0]]) {
    const scale = captureScale(width, height);
    assert.ok(Number.isFinite(scale) && scale > 0 && scale <= 2);
    assert.ok(width * scale <= 16000.001);
    assert.ok(height * scale <= 30000.001);
    assert.ok(width * height * scale ** 2 <= 45000000.001);
  }
});
