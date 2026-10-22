// @ts-check
// Geometria de las graficas de Operativa. Funciones puras: reciben cifras y
// devuelven posiciones; dibujar es trabajo de los componentes de ui/.

const DONUT_RADIUS = 64;
const CIRCUMFERENCE = 2 * Math.PI * DONUT_RADIUS;

/** @param {number} value */
const round1 = (value) => Math.round(value * 10) / 10;

/**
 * Trazo de cada arco de la dona de salud, en el orden de los conteos.
 * @param {number[]} counts Proyectos por estado.
 * @returns {{dash: number, gap: number, offset: number}[]}
 */
export function donutArcs(counts) {
  const total = counts.reduce((sum, n) => sum + n, 0);
  let consumed = 0;
  return counts.map((count) => {
    const dash = total ? (CIRCUMFERENCE * count) / total : 0;
    const arc = { dash: round1(dash), gap: round1(CIRCUMFERENCE - dash), offset: round1(-consumed) + 0 };
    consumed += dash;
    return arc;
  });
}

export const DONUT = Object.freeze({ radius: DONUT_RADIUS, circumference: CIRCUMFERENCE });

const BARS = { left: 14, width: 506, ratio: 0.71, maxBar: 40, baseline: 100, perPoint: 0.78, maxPercent: 115, textGap: 6 };

/** 68 -> "68%", 99.5 -> "99.5%", sin dato -> "—". @param {number | null | undefined} value */
export function percentText(value) {
  if (value === null || value === undefined) return '—';
  const rounded = round1(value);
  return `${rounded}%`;
}

/**
 * Posicion de cada barra de la grafica mensual (SVG de 520 x 126).
 * @param {(number | null)[]} percents Facturabilidad global por mes.
 */
export function billingBars(percents) {
  if (!percents.length) return [];
  const slot = BARS.width / percents.length;
  const width = round1(Math.min(slot * BARS.ratio, BARS.maxBar));
  return percents.map((percent, index) => {
    const shown = Math.min(Math.max(percent ?? 0, 0), BARS.maxPercent);
    const height = round1(shown * BARS.perPoint);
    const x = round1(BARS.left + index * slot + (slot - width) / 2);
    return {
      x,
      y: round1(BARS.baseline - height),
      width,
      height,
      center: round1(x + width / 2),
      textY: round1(BARS.baseline - height - BARS.textGap),
    };
  });
}
