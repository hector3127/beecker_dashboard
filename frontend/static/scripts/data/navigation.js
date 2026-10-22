// @ts-check
// Enlaces a pantallas de detalle: llevan el periodo elegido y la pagina actual
// en ?volver=, para que el boton de regreso vuelva a ella tal como estaba.
// El servidor valida el destino (return_context); aqui solo se construye.

const PERIOD_KEYS = ['periodo', 'anio', 'mes', 'trimestre', 'desde', 'hasta'];

/**
 * @param {string} href Enlace al detalle (ruta local).
 * @param {Pick<Location, 'origin' | 'pathname' | 'search' | 'hash'>} [here]
 * @returns {string} El enlace con periodo y volver; uno de otro origen no cambia.
 */
export function withReturn(href, here = location) {
  const url = new URL(href, here.origin);
  if (url.origin !== here.origin) return href;
  const source = new URLSearchParams(here.search);
  if (source.has('periodo') && !url.searchParams.has('periodo')) {
    for (const key of PERIOD_KEYS) if (source.has(key)) url.searchParams.set(key, /** @type {string} */ (source.get(key)));
  }
  url.searchParams.set('volver', here.pathname + here.search + here.hash);
  return url.pathname + url.search + url.hash;
}
