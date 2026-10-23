// @ts-check
// Totales que la pantalla de una cuenta muestra a partir de sus proyectos:
// avance promedio, modelos de servicio, estados y alertas. Son sumas de lo
// que ya esta en pantalla (las horas llegan por lotes), no reglas de negocio.

const PALETTE = ['#24bc86', '#6540ed', '#f5b326', '#ec4d79', '#b1abc4'];
const NO_SERVICE = 'Sin servicio';

/** Redondeo al par mas cercano, como el round() del servidor. @param {number} value */
export function roundHalfEven(value) {
  const floor = Math.floor(value);
  const diff = value - floor;
  if (Math.abs(diff - 0.5) < 1e-9) return floor % 2 === 0 ? floor : floor + 1;
  return Math.round(value);
}

/** "ixb" y "IxB" son el mismo servicio. @param {{service?: string | null}} project */
export function serviceName(project) {
  const raw = String(project.service || NO_SERVICE);
  return /^ixb$/i.test(raw) ? 'IxB' : raw;
}

/** @param {any} project */
export const isAlert = (project) => Boolean(project.exceeded || project.late);

/**
 * Avance promedio de los proyectos con presupuesto y consumo ya conocido.
 * @param {any[]} projects
 * @returns {number | null}
 */
export function averageProgress(projects) {
  const known = projects.filter((p) => p.budget && p.burn !== null && p.burn !== undefined && !p.clockify_pending);
  if (!known.length) return null;
  return known.reduce((sum, p) => sum + (p.burn / p.budget) * 100, 0) / known.length;
}

/**
 * Avance por modelo de servicio: completados, otras etapas y con alertas (%).
 * @param {any[]} projects
 */
export function serviceModels(projects) {
  /** @type {Map<string, any[]>} */
  const groups = new Map();
  for (const project of projects) {
    const key = project.service || NO_SERVICE;
    groups.set(key, [...(groups.get(key) || []), project]);
  }
  return [...groups.entries()].map(([name, subset]) => {
    const share = (/** @type {(p: any) => boolean} */ test) => roundHalfEven((subset.filter(test).length / subset.length) * 100);
    const completed = share((p) => ['completed', 'completado'].includes(String(p.stage || '').toLowerCase()) && !isAlert(p));
    const risk = share(isAlert);
    return { name, count: subset.length, completed, risk, other: Math.max(0, 100 - completed - risk) };
  });
}

/**
 * Proyectos por estado, con lo que necesita la dona: porcentaje, tramo y color.
 * @param {any[]} projects
 */
export function stateSlices(projects) {
  /** @type {Map<string, number>} */
  const counts = new Map();
  for (const project of projects) {
    const state = project.state || 'Sin estado';
    counts.set(state, (counts.get(state) || 0) + 1);
  }
  let running = 0;
  return [...counts.entries()].map(([name, count], index) => {
    const percent = (count / projects.length) * 100;
    const slice = { name, count, percent: roundHalfEven(percent), dash: percent, offset: -running, color: PALETTE[index % PALETTE.length] };
    running += percent;
    return slice;
  });
}

/**
 * Presupuesto y consumo por servicio, para la grafica de barras.
 * @param {any[]} projects
 */
export function serviceHours(projects) {
  /** @type {Map<string, {budget: number, burn: number}>} */
  const groups = new Map();
  for (const project of projects) {
    const key = serviceName(project);
    const group = groups.get(key) || { budget: 0, burn: 0 };
    group.budget += Number(project.budget || 0);
    group.burn += Number(project.burn || 0);
    groups.set(key, group);
  }
  return groups;
}
