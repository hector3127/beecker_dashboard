// @ts-check
// Al abrir una cuenta, un proyecto, el detalle de costos o la comparativa de
// margenes, el enlace lleva ?volver= con la pantalla actual (y su cadena de
// regreso) y conserva el periodo elegido. Igual que en la pantalla anterior.

const TARGETS = /^\/(?:cuenta\/[^/]+\/|proyectos\/[^/]+\/|ejecutiva\/costos\/detalle\/|ejecutiva\/oportunidades\/)$/;
const PERIOD_KEYS = ['periodo', 'anio', 'mes', 'trimestre', 'desde', 'hasta'];

/**
 * @param {URL} link Destino del enlace.
 * @param {URL} source Pantalla actual.
 * @returns {string | null} El destino con regreso, o null si no aplica.
 */
export function withReturn(link, source) {
  if (link.origin !== source.origin || !TARGETS.test(link.pathname)) return null;
  const target = new URL(link.href);
  if (source.searchParams.has('periodo') && !target.searchParams.has('periodo')) {
    for (const key of PERIOD_KEYS) {
      if (source.searchParams.has(key)) target.searchParams.set(key, /** @type {string} */ (source.searchParams.get(key)));
    }
  }
  target.searchParams.set('volver', source.pathname + source.search + source.hash);
  return target.href;
}

if (typeof document !== 'undefined') {
  document.addEventListener('click', (event) => {
    const link = /** @type {HTMLAnchorElement | null} */ ((/** @type {Element} */ (event.target)).closest('a[href]'));
    if (!link || link.hasAttribute('data-portal-back') || link.classList.contains('cost-back')) return;
    const next = withReturn(new URL(link.href, location.href), new URL(location.href));
    if (next) link.href = next;
  });
}
