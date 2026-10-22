// @ts-check
// Totales de lo que la cuenta muestra, calculados sobre sus proyectos. Las
// horas llegan por lotes despues de abrir la pagina, asi que se recalculan
// aqui con las mismas reglas cada vez. Sin DOM: se prueba con node.
import { plain } from '#app/lib/format.js';

/**
 * @typedef {object} AccountProject
 * @property {string} id
 * @property {string | null} [name]
 * @property {string | null} [service]
 * @property {string | null} [stage]
 * @property {string | null} [state]
 * @property {string | null} [manager]
 * @property {number | null} [budget]
 * @property {number | null} [burn]
 * @property {number | null} [nps]
 * @property {boolean} [clockify_pending]
 * @property {boolean} [late]
 * @property {boolean} [clockify_error] Las horas no se pudieron leer.
 */

/** IxB se escribe distinto en cada hoja. @param {AccountProject} project */
export function serviceName(project) {
  const raw = String(project.service || 'Sin servicio');
  return /^ixb$/i.test(raw) ? 'IxB' : raw;
}

/** Consumo mayor que un presupuesto conocido. @param {AccountProject} project */
export function isOverBudget(project) {
  return project.burn != null && Number(project.budget) > 0 && project.burn > Number(project.budget);
}

/** @param {AccountProject} project */
const isAtRisk = (project) => isOverBudget(project) || Boolean(project.late);

/** @param {AccountProject[]} projects */
export function hourTotals(projects) {
  const burn = projects.reduce((sum, p) => sum + Number(p.burn || 0), 0);
  const budget = projects.reduce((sum, p) => sum + Number(p.budget || 0), 0);
  return { burn, budget, ratio: budget > 0 ? (burn / budget) * 100 : null };
}

/**
 * Promedio de consumo/presupuesto de los proyectos con ambos datos.
 * @param {AccountProject[]} projects
 * @returns {number | null}
 */
export function averageProgress(projects) {
  const known = projects.filter((p) => Number(p.budget) > 0 && p.burn != null && !p.clockify_pending);
  if (!known.length) return null;
  return known.reduce((sum, p) => sum + (/** @type {number} */ (p.burn) / Number(p.budget)) * 100, 0) / known.length;
}

/**
 * Por modelo de servicio: proyectos, horas y reparto completados / otros / en riesgo.
 * @param {AccountProject[]} projects
 */
export function byService(projects) {
  /** @type {Map<string, AccountProject[]>} */
  const groups = new Map();
  for (const project of projects) {
    const name = serviceName(project);
    groups.set(name, [...(groups.get(name) || []), project]);
  }
  return [...groups].map(([name, items]) => {
    const completed = Math.round(
      (items.filter((p) => /^(completed|completado)$/i.test(String(p.stage || '')) && !isAtRisk(p)).length / items.length) * 100,
    );
    const risk = Math.round((items.filter(isAtRisk).length / items.length) * 100);
    return { name, count: items.length, ...hourTotals(items), completed, risk, other: Math.max(0, 100 - completed - risk) };
  });
}

/** @param {AccountProject[]} projects */
export function stateCounts(projects) {
  /** @type {Map<string, number>} */
  const counts = new Map();
  for (const project of projects) {
    const name = project.state || 'Sin estado';
    counts.set(name, (counts.get(name) || 0) + 1);
  }
  return [...counts].map(([name, count]) => ({ name, count, percent: Math.round((count / projects.length) * 100) }));
}

/** @param {AccountProject[]} projects */
export function alerts(projects) {
  return projects
    .filter(isAtRisk)
    .map((project) => ({ project, reason: isOverBudget(project) ? 'Consumo mayor que el presupuesto' : 'Fecha vencida' }));
}

/** @param {AccountProject[]} projects */
export const npsProjects = (projects) => projects.filter((p) => p.nps != null);

/** @param {AccountProject[]} projects @returns {number | null} */
export function npsAverage(projects) {
  const rated = npsProjects(projects);
  return rated.length ? rated.reduce((sum, p) => sum + Number(p.nps), 0) / rated.length : null;
}

/** Color de la pastilla segun el texto de la etapa o el estado. @param {string | null | undefined} text */
export function stageTone(text) {
  const value = String(text || '').trim().toLowerCase();
  if (/completed|completado|finalizado|producción/.test(value)) return 'green';
  if (/cancel/.test(value)) return 'red';
  if (/suspend/.test(value)) return 'yellow';
  return 'purple';
}

/**
 * @template T
 * @param {T[]} items
 * @param {number} page Empieza en 1; se ajusta al rango valido.
 * @param {number} size
 */
export function pageOf(items, page, size) {
  const pages = Math.max(1, Math.ceil(items.length / size));
  const current = Math.max(1, Math.min(page, pages));
  const from = (current - 1) * size;
  return { items: items.slice(from, from + size), page: current, pages, from: items.length ? from + 1 : 0, to: Math.min(from + size, items.length) };
}

/**
 * Lo que muestra el analisis de presupuesto contra consumo: solo proyectos con
 * horas ya leidas, filtrados por servicio y busqueda.
 * @param {AccountProject[]} projects
 * @param {{service?: string, search?: string, by?: 'service' | 'project'}} [options]
 */
export function budgetView(projects, { service = '', search = '', by = 'service' } = {}) {
  const needle = plain(search);
  const selected = projects.filter(
    (p) => !p.clockify_pending && p.burn != null && (!service || serviceName(p) === service) && plain(`${p.id} ${p.name || ''}`).includes(needle),
  );
  const totals = hourTotals(selected);
  /** @param {(p: AccountProject) => string} key */
  const group = (key) => {
    /** @type {Map<string, {name: string, budget: number, burn: number}>} */
    const found = new Map();
    for (const p of selected) {
      const name = key(p);
      const item = found.get(name) || { name, budget: 0, burn: 0 };
      item.budget += Number(p.budget || 0);
      item.burn += Number(p.burn || 0);
      found.set(name, item);
    }
    return [...found.values()].sort((a, b) => a.name.localeCompare(b.name, 'es'));
  };
  const services = group(serviceName).map((s) => ({ ...s, percent: totals.burn ? (s.burn / totals.burn) * 100 : 0 }));
  return {
    selected,
    totals,
    exceeded: selected.filter(isOverBudget).length,
    groups: by === 'service' ? services : group((p) => p.id),
    services,
  };
}
