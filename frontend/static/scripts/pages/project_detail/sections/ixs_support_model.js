import { dateMs, phases, resourceKey } from "./ixs_executive_model.js";

export function applyResourceStates(project, result) {
  const states = new Map(
    (result.filas || []).map((row) => [resourceKey(row.nombre), row.activo]),
  );
  (project.filasRecursosCompleto || []).forEach((row) => {
    if (states.has(resourceKey(row.nombre)))
      row.activo = states.get(resourceKey(row.nombre));
  });
}

export function isoDate(value) {
  const ms = dateMs(value);
  if (!Number.isFinite(ms)) return "";
  const date = new Date(ms),
    pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
const STAGES = ["Discovery", "Development", "Deployment"];
const stageOf = (name) => {
  const match = String(name || "").match(/discovery|development|deployment/i);
  return match
    ? STAGES.find((stage) => stage.toLowerCase() === match[0].toLowerCase())
    : "";
};

export function suggestedDates(data) {
  const project = data || {},
    history = phases(project),
    plan = project.hitos || [],
    closes = {};
  STAGES.forEach((stage) => {
    const real = history
      .filter((row) => stageOf(row.name) === stage)
      .sort((a, b) => dateMs(b.end) - dateMs(a.end))[0];
    const estimated = plan
      .filter((row) => stageOf(row.nombre) === stage && row.fechaFinPlan)
      .sort((a, b) => dateMs(b.fechaFinPlan) - dateMs(a.fechaFinPlan))[0];
    const raw =
      real && !real.active
        ? real.end
        : estimated
          ? estimated.fechaFinPlan
          : real
            ? real.end
            : "";
    closes[stage] = isoDate(raw);
  });
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  const inRange = (row) =>
    dateMs(row.start) <= today.getTime() &&
    today.getTime() <= dateMs(row.end || row.start);
  const known = history.filter((row) => stageOf(row.name));
  const current =
    known.find((row) => row.active) ||
    known.find(inRange) ||
    known
      .slice()
      .sort((a, b) => dateMs(b.end || b.start) - dateMs(a.end || a.start))[0];
  return { stage: current ? stageOf(current.name) : "", closes };
}
