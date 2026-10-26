// Presentation rules of the original deferred RAID and Clockify panels.
export function hoursText(value) {
  const hours = Number(value || 0);
  return (
    (Math.round(hours * 100) / 100).toLocaleString("es-MX", {
      maximumFractionDigits: 2,
    }) + " h"
  );
}

export function impactClass(value) {
  if (!value) return "";
  const level = value.toLowerCase();
  if (level === "alto") return "badge-alto";
  if (level === "medio") return "badge-medio";
  if (level === "bajo") return "badge-bajo";
  return "";
}

export function tasksModel(result) {
  const tasks = result.tasks || [];
  return {
    operational: hoursText(result.invOperativa),
    commercial: hoursText(result.invComercial),
    total: hoursText(result.totalHoras),
    heading:
      "HORAS POR TASK" +
      (result.nomenclatura ? ` · ${result.nomenclatura}` : ""),
    range: result.rango
      ? `Rango: ${String(result.rango.fechaInicio || "").slice(0, 10)} → ${String(result.rango.fechaFin || "").slice(0, 10)} · Tasks activas`
      : "",
    withHours: tasks
      .filter((task) => Number(task.horas || 0) > 0)
      .map((task) => ({
        name: String(task.nombre || "Sin task"),
        hours: hoursText(task.horas),
      })),
    // Negative hours belong in the original zero-hours disclosure as well.
    withoutHours: tasks
      .filter((task) => Number(task.horas || 0) <= 0)
      .map((task) => String(task.nombre || "Sin task")),
  };
}

export function raidModel(result) {
  return {
    rows: (result.riesgos || []).map((risk) => ({
      description: String(risk.descripcion || ""),
      detail: `#${risk.id} · ${risk.estado || ""}${risk.severity ? " · Severity: " + risk.severity : ""}`,
      impact: String(risk.impacto || "Medio"),
      badge: impactClass(risk.impacto),
      probability: String(risk.probabilidad || "—"),
    })),
    totals: [
      result.totalRiesgos,
      result.totalPendientes,
      result.totalOportunidades,
    ].map((value) => String(value || 0)),
  };
}
