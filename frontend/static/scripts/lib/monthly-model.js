// @ts-check
// Geometria de la grafica de rentabilidad mensual: barras de facturacion y
// costos con la linea de margen. Solo calcula posiciones; dibujar es de ui/.

/**
 * @typedef {object} MonthRow
 * @property {string} month AAAA-MM
 * @property {number} revenue
 * @property {number | null} [cost]
 * @property {number | null} [margin]
 */

const TOP = 32;
const BASELINE = 222;

/**
 * @param {{months?: MonthRow[], complete?: boolean}} data
 * @param {number} viewportWidth Ancho disponible; se respeta aunque sea angosto.
 */
export function monthlyModel(data, viewportWidth) {
  const rows = data.months || [];
  const viewport = Math.max(240, Number(viewportWidth) || 900);
  const width = rows.length > 6 ? Math.max(viewport, 120 + rows.length * 84) : viewport;
  const left = viewport < 500 ? 53 : 72;
  const right = viewport < 500 ? 43 : 55;
  const step = (width - left - right) / Math.max(1, rows.length);
  const barWidth = Math.max(6, Math.min(36, (step - 12) / 2));
  const values = rows.flatMap((row) => [row.revenue, row.cost ?? 0]);
  const maximum = Math.max(1, ...values);
  const minimum = Math.min(0, ...values);
  const span = maximum - minimum;
  const y = (/** @type {number} */ value) => BASELINE - ((value - minimum) * (BASELINE - TOP)) / span;
  const margins = rows.filter((row) => row.margin != null).map((row) => /** @type {number} */ (row.margin));
  const marginMin = Math.min(0, ...margins);
  const marginMax = Math.max(100, ...margins);
  const marginY = (/** @type {number} */ value) => BASELINE - ((value - marginMin) * (BASELINE - TOP)) / (marginMax - marginMin);
  const zero = y(0);

  /** @param {number | null | undefined} value @param {number} x */
  const bar = (value, x) =>
    value == null ? null : { x, y: Math.min(zero, y(value)), height: Math.abs(zero - y(value)), width: barWidth, value };

  /** Segmentos continuos de la linea: un mes sin margen la corta. @type {{x: number, y: number, value: number, month: string}[][]} */
  const segments = [];
  let current = /** @type {{x: number, y: number, value: number, month: string}[]} */ ([]);
  const columns = rows.map((row, index) => {
    const center = left + step * (index + 0.5);
    if (row.margin != null) current.push({ x: center, y: marginY(row.margin), value: row.margin, month: row.month });
    else if (current.length) {
      segments.push(current);
      current = [];
    }
    return { month: row.month, center, revenue: bar(row.revenue, center - barWidth - 2), cost: bar(row.cost, center + 2) };
  });
  if (current.length) segments.push(current);

  return {
    width,
    left,
    right,
    step,
    top: TOP,
    baseline: BASELINE,
    columns,
    segments,
    leftTicks: [0, 1, 2, 3].map((i) => ({ y: BASELINE - (i * (BASELINE - TOP)) / 3, value: minimum + (span * i) / 3 })),
    rightTicks: margins.length
      ? [0, 1, 2, 3].map((i) => ({ y: BASELINE - (i * (BASELINE - TOP)) / 3, value: Math.round(marginMin + ((marginMax - marginMin) * i) / 3) }))
      : [],
  };
}
