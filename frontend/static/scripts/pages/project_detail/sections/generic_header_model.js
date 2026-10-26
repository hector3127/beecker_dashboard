import { shortDate } from "./generic_panels_model.js";

// Original display rules; lifecycle/state decisions are supplied by the caller.
export function genericHeaderModel(data, context) {
  const p = data.proyecto,
    av = data.avance,
    pr = data.presupuesto;
  const ke = data.kpisExtra || { pctCumplimientoFinanciero: 0 };
  const circle = 2 * Math.PI * 33.5;
  const arc = (Math.max(0, Math.min(100, av.pct)) / 100) * circle;
  return {
    project: `${p.id} - ${p.nombre}`,
    client: String(p.cliente),
    cut: shortDate(p.fechaCorte),
    sponsor: String(p.sponsor || "—"),
    manager: String(p.pm || "—"),
    delivery: p.deliveryManager ? `DM: ${p.deliveryManager}` : "",
    state: String(p.estadoGeneral),
    color: context.color,
    progress: { arc, rest: circle - arc, label: Math.round(av.pct) + "%" },
    planned:
      av.pctTiempoTranscurrido != null
        ? `Planificado: ${av.pctTiempoTranscurrido}%`
        : "",
    pace: av.indiceRitmo != null ? String(av.indiceRitmo) : "—",
    paceDown:
      av.indiceRitmo != null && av.indiceRitmo > 1.1 && !context.completed,
    paceText: context.completed
      ? "Proyecto completado"
      : av.indiceRitmo == null
        ? "Sin fechas"
        : av.indiceRitmo > 1.1
          ? "Por encima del plan"
          : "En plan / eficiente",
    financial: ke.pctCumplimientoFinanciero + "%",
    budget: pr.budget.toLocaleString(),
    burn: pr.burn.toLocaleString(),
    remaining: pr.etc.toLocaleString(),
    budgetWidth: pr.pctEjecutado + "%",
    exitTitle: context.prd ? "Fecha de salida a PRD" : "Fecha Est. de Salida",
    exitDate: context.prd
      ? context.prdDate
        ? shortDate(context.prdDate)
        : "—"
      : shortDate(p.fechaFinEstimada),
    exitText: context.prd
      ? "Fin de Deployment"
      : `Riesgo ${p.nivelRiesgoFecha}`,
    exitClass: context.prd ? "" : "badge " + context.riskClass,
  };
}
