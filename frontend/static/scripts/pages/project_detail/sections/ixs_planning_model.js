import { dateMs, milestones, resourceKey } from "./ixs_executive_model.js";

export function planningStatus(state) {
  const value = String(state || "")
    .trim()
    .toUpperCase();
  if (value === "CANCELLED") return "cancelled";
  if (
    ["NOT APPLICABLE", "CLOSED", "REJECTED", "COMPLETED", "INACTIVE"].includes(
      value,
    )
  )
    return "closed";
  return value === "ACTIVE"
    ? "active"
    : value === "PROPOSED"
      ? "proposed"
      : value === "BLOCKED"
        ? "blocked"
        : "other";
}

export function planningSummary(plan, azure) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const start = today.getTime(),
    week = start + 7 * 86400000,
    month = start + 30 * 86400000;
  const abiertas = azure.items.filter(
    (x) => !["closed", "cancelled"].includes(planningStatus(x.estado)),
  );
  const dated = abiertas
    .map((x) => ({ ...x, limite: dateMs(x.fechaLimiteDev) }))
    .filter((x) => Number.isFinite(x.limite));
  const vacaciones = plan.vacaciones
    .filter(
      (x) =>
        !/cancel|rechaz/i.test(x.estado || "") &&
        Number.isFinite(dateMs(x.inicio)) &&
        dateMs(x.fin) >= start &&
        dateMs(x.inicio) <= month,
    )
    .sort((a, b) => dateMs(a.inicio) - dateMs(b.inicio));
  return {
    abiertas,
    late: dated
      .filter((x) => x.limite < start)
      .sort((a, b) => a.limite - b.limite),
    soon: dated
      .filter((x) => x.limite >= start && x.limite <= week)
      .sort((a, b) => a.limite - b.limite),
    vacaciones,
  };
}

export function planningModel(data, plan, azure) {
  const summary = planningSummary(plan, azure),
    hitos = milestones(data).filter((x) => !x.extra);
  const completed = hitos.filter((x) => x.state === "Completado").length,
    underway = hitos.filter((x) => x.state === "En curso").length;
  const items = azure.items || [],
    closed = items.filter((x) => planningStatus(x.estado) === "closed").length;
  const byStage = new Map();
  items.forEach((x) => {
    const path = String(x.iterationPath || "").trim();
    const stage = path
      ? path.split("\\").filter(Boolean).pop()
      : "Sin iteración";
    byStage.set(stage, (byStage.get(stage) || 0) + 1);
  });
  const dated = items.filter((x) =>
    Number.isFinite(dateMs(x.fechaLimiteDev)),
  ).length;
  const resources = (data.filasRecursosCompleto || []).filter(
    (x) => x.nombre,
  ).length;
  const start = new Date();
  start.setHours(12, 0, 0, 0);
  const weeks = Array.from({ length: 6 }, (_, i) => {
    const from = new Date(start.getTime() + i * 7 * 86400000),
      to = new Date(from.getTime() + 6 * 86400000);
    const count = new Set(
      plan.vacaciones
        .filter(
          (v) =>
            !/cancel|rechaz/i.test(v.estado || "") &&
            dateMs(v.inicio) <= to.getTime() &&
            dateMs(v.fin) >= from.getTime(),
        )
        .map((v) => resourceKey(v.recurso)),
    ).size;
    return {
      fecha: from.toLocaleDateString("es-MX", {
        day: "numeric",
        month: "short",
      }),
      count,
    };
  });
  return {
    summary,
    hitos,
    completed,
    underway,
    items,
    closed,
    dated,
    resources,
    weeks,
    byStage: [...byStage].sort((a, b) => b[1] - a[1]).slice(0, 4),
    timeline: {
      ...data,
      hitosAdicionales: (data.hitosAdicionales || []).concat(
        plan.compromisos
          .filter((x) => x.tipo === "Hito")
          .map((x) => ({
            tipo: x.actividad,
            fecha: x.fecha,
            observacion: x.estado,
          })),
      ),
    },
  };
}
