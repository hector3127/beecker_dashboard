// Presentation only: original rounding, defaults, grouping and date format.
export function resourceStateClass(state) {
  if (state === "Retrasado" || state === "Excedido") return "badge-error";
  if (state === "En riesgo") return "badge-warning";
  return "badge-ok";
}

export function resourcesModel(data) {
  const total = data.totalesRecursos || {};
  return {
    rows: (data.filasRecursosCompleto || []).map((row) => ({
      cells: [
        row.posicion,
        row.nombre,
        row.banda,
        "$" + row.costingRate,
        row.horasEstimadas,
        row.horasReales,
        row.horasNoFact,
        row.balance,
        row.pctCumplimiento + "%",
        "$" + Math.round(row.costoReal).toLocaleString(),
      ].map(String),
      state: String(row.estado),
      badge: resourceStateClass(row.estado),
    })),
    totals: [
      total.horasEstimadas || 0,
      total.horasReales || 0,
      total.horasNoFact || 0,
      total.balance || 0,
      (total.pctCumplimientoHoras || 0) + "%",
      "$" + Math.round(total.costoReal || 0).toLocaleString(),
      (total.pctCumplimientoFinanciero || 0) + "% financiero",
    ].map(String),
  };
}

export function shortDate(value) {
  if (!value) return "?";
  const date = new Date(value);
  if (isNaN(date.getTime())) return "?";
  return date.toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function milestonesModel(rows) {
  const present = (row) => ({
    name: String(row.nombre),
    date: shortDate(row.fechaFinPlan),
    subtitle: row.esAdicional
      ? `Fecha: ${shortDate(row.fechaFinPlan)}`
      : `Inicio: ${shortDate(row.fechaInicioPlan)} · Fin: ${shortDate(row.fechaFinPlan)}`,
    note: row.esAdicional && row.observacion ? `"${row.observacion}"` : "",
    status:
      {
        Completado: "complete",
        "En curso": "running",
        Suspendida: "suspended",
      }[row.estado] || "pending",
  });
  return {
    upcoming: rows.filter((row) => row.estado !== "Completado").map(present),
    completed: rows.filter((row) => row.estado === "Completado").map(present),
  };
}
