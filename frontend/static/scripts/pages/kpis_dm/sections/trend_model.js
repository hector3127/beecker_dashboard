// @ts-check
// Shape-preserving interpolation: points are observations, curves are visual.
/** @typedef {{x: number, y: number}} Point */

/**
 * Monotone cubic Hermite controls, limited to each pair's value range.
 * @param {Point[]} points Equally spaced monthly observations in one run.
 * @returns {{start: Point, c1: Point, c2: Point, end: Point}[]}
 */
export function trendSegments(points) {
  if (points.length < 2) return [];
  const slopes = points
    .slice(1)
    .map((p, i) => (p.y - points[i].y) / (p.x - points[i].x));
  const tangents = points.map((_, i) => {
    if (i === 0) return slopes[0];
    if (i === points.length - 1) return slopes[i - 1];
    const before = slopes[i - 1],
      after = slopes[i];
    return before * after <= 0 ? 0 : (2 * before * after) / (before + after);
  });
  slopes.forEach((slope, i) => {
    if (slope === 0) {
      tangents[i] = tangents[i + 1] = 0;
      return;
    }
    const length = Math.hypot(tangents[i] / slope, tangents[i + 1] / slope);
    if (length > 3) {
      tangents[i] = (3 * tangents[i]) / length;
      tangents[i + 1] = (3 * tangents[i + 1]) / length;
    }
  });
  return points.slice(1).map((end, i) => {
    const start = points[i],
      third = (end.x - start.x) / 3;
    return {
      start,
      end,
      c1: { x: start.x + third, y: start.y + third * tangents[i] },
      c2: { x: end.x - third, y: end.y - third * tangents[i + 1] },
    };
  });
}

/**
 * Split at absent observations: never interpolate a missing month as zero.
 * @param {(Point | null)[]} observations
 * @returns {string} SVG path through every known observation.
 */
export function trendPath(observations) {
  let path = "";
  /** @type {Point[]} */
  let run = [];
  function flush() {
    if (!run.length) return;
    path += `M${run[0].x} ${run[0].y}`;
    for (const { c1, c2, end } of trendSegments(run)) {
      path += `C${c1.x} ${c1.y} ${c2.x} ${c2.y} ${end.x} ${end.y}`;
    }
    run = [];
  }
  for (const point of observations) {
    if (point) run.push(point);
    else flush();
  }
  flush();
  return path;
}
