// @ts-check
// Los filtros de una pantalla viven en la URL: se pueden compartir, recargar
// y el boton de regreso los conserva.

/**
 * Devuelve la URL con los valores dados; null, undefined o "" quitan el parametro.
 * @param {string} href
 * @param {Record<string, unknown>} values
 */
export function withParams(href, values) {
  const url = new URL(href, 'http://local.invalid');
  for (const [key, value] of Object.entries(values)) {
    if (value === null || value === undefined || value === '') url.searchParams.delete(key);
    else url.searchParams.set(key, String(value));
  }
  return url.pathname + url.search + url.hash;
}

/** @param {string} [search] */
export const readParams = (search = location.search) => new URLSearchParams(search);

/**
 * Actualiza los filtros en la URL sin recargar.
 * @param {Record<string, unknown>} values
 * @param {{push?: boolean}} [options] push=true agrega una entrada al historial.
 */
export function writeParams(values, options = {}) {
  const next = withParams(location.href, values);
  history[options.push ? 'pushState' : 'replaceState'](history.state, '', next);
}
