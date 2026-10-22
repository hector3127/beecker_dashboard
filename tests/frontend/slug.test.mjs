import { test } from 'node:test';
import assert from 'node:assert/strict';

import { slugify } from '../../frontend/static/scripts/lib/slug.js';

// Cada par sale de apps/portal/services/slugs.build_slug: la direccion de una
// cuenta se arma en el navegador y la resuelve el servidor.
test('slugify gives the same result as the server', () => {
  const pairs = [
    ['Clínica Sur', 'clinica-sur'],
    ['  Nestlé México  ', 'nestle-mexico'],
    ['ACME & Co.', 'acme-co'],
    ['Ñandú', 'nandu'],
    ['日本', 'sin-nombre'],
    ['T&M', 't-m'],
    ['', 'sin-nombre'],
    ['Heineken México', 'heineken-mexico'],
  ];
  for (const [name, expected] of pairs) assert.equal(slugify(name), expected, name);
});
