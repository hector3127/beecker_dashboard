// @ts-check
/** @param {any[]} projects */
export function costCoverage(projects) {
  const included = projects.filter(project => !project.future);
  return {
    total: included.length,
    complete: included.filter(project => project.complete).length,
    partial: included.filter(project => !project.complete && project.cost !== null && project.cost !== undefined).length,
    missing: included.filter(project => !project.complete && (project.cost === null || project.cost === undefined)).length,
    future: projects.length - included.length,
  };
}

/** @param {any[]} projects @param {string | null} loadedAt */
export function verifiedCostBlockers(projects, loadedAt) {
  if (!loadedAt) return [];
  return projects.filter(project =>
    !project.complete && !project.future &&
    (project.cost != null || Boolean(project.error?.trim()))
  );
}
