// @ts-check
// Escala y trazos de la grafica de C por mes. Sin DOM: se prueba con node.

const valid = (/** @type {unknown} */ v) => typeof v === 'number' && Number.isFinite(v);

/**
 * Rango vertical y marcas. La escala ampliada acerca los valores; la completa
 * va de 0 a 100 como minimo.
 * @param {(number | null)[]} values
 * @param {boolean} complete
 */
export function chartScale(values, complete) {
  const known = values.filter(valid);
  const low = known.length ? Math.min(...known) : 0;
  const high = known.length ? Math.max(...known) : 100;
  const minimum = complete
    ? Math.min(0, Math.floor(low / 10) * 10)
    : low >= 0
      ? Math.max(0, Math.floor((low - 5) / 10) * 10)
      : Math.floor((low - 5) / 10) * 10;
  const maximum = complete ? Math.max(100, Math.ceil(high / 10) * 10) : Math.max(minimum + 10, Math.ceil((high + 5) / 10) * 10);
  const interval = complete && minimum === 0 && maximum === 100 ? 25 : maximum - minimum <= 20 ? 5 : Math.ceil((maximum - minimum) / 5 / 10) * 10;
  const ticks = [];
  for (let value = minimum; value <= maximum; value += interval) ticks.push(value);
  if (ticks[ticks.length - 1] !== maximum) ticks.push(maximum);
  return { minimum, maximum, ticks, hasValues: known.length > 0 };
}

/**
 * Trazo de una serie: un valor que falta corta la linea.
 * @param {(number | null)[]} values
 * @param {(i: number) => number} x
 * @param {(v: number) => number} y
 */
export function seriesPath(values, x, y) {
  let path = '';
  let connected = false;
  values.forEach((value, i) => {
    if (!valid(value)) {
      connected = false;
      return;
    }
    path += `${connected ? 'L' : 'M'}${x(i)} ${y(/** @type {number} */ (value))}`;
    connected = true;
  });
  return path;
}
