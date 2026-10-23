// @ts-check
// Empty selection means the whole account; totals always describe visible rows.
/** @param {any} report @param {Set<string>} ids */
export function selectProjects(report, ids) {
  if (!ids.size) return report;
  const projects = report.projects.filter((/** @type {any} */ row) => ids.has(row.id));
  const totals = report.months.map((/** @type {any} */ _, /** @type {number} */ i) => ({
    hours: projects.some((/** @type {any} */ row) => row.cells[i].hours != null)
      ? Math.round(projects.reduce((/** @type {number} */ sum, /** @type {any} */ row) => sum + (row.cells[i].hours ?? 0), 0) * 10000) / 10000 : null,
    partial: projects.some((/** @type {any} */ row) => row.cells[i].partial),
  }));
  return { ...report, projects, totals,
    known_hours: Math.round(projects.reduce((/** @type {number} */ sum, /** @type {any} */ row) => sum + row.known_hours, 0) * 10000) / 10000,
    partial: totals.some((/** @type {any} */ cell) => cell.partial),
  };
}
