import { genericTimeline } from "./generic_timeline_model.js";
import { prdDate } from "./ixs_executive_model.js";

// Same lifecycle decisions as the transitional renderer, without mutating data.
export function genericExecutiveModel(data, metadata = {}, now = Date.now()) {
  const p = data.proyecto;
  const service = String(
    (metadata[String(p.id || "")] || {}).servicio || p.servicio || "",
  );
  const prd = /\b(?:ixb|raas|saas)\b/i.test(service);
  const timeline =
    data.hitos && data.hitos.length ? genericTimeline(data, now) : null;
  const completed = !!timeline?.proyectoCompletadoDetectado;
  const colors = {
    verde: "#2E7D32",
    amarillo: "#F2A900",
    rojo: "#C62828",
    gris: "#8D8D91",
  };
  return {
    timeline,
    now,
    milestones: data.hitosAdicionales || [],
    summary: timeline?.hitosResumenCorregido || [],
    // The caller applies precisely the two original completion assignments.
    projectPatch: completed
      ? { estadoGeneral: "COMPLETADO", nivelRiesgoFecha: "Completado" }
      : {},
    context: {
      color: completed ? colors.verde : colors[p.estadoColor] || colors.verde,
      riskClass: completed
        ? "badge-bajo"
        : p.nivelRiesgoFecha === "Alto"
          ? "badge-alto"
          : p.nivelRiesgoFecha === "Medio"
            ? "badge-medio"
            : "badge-bajo",
      prd,
      prdDate: prd ? prdDate(data) : "",
      completed,
    },
  };
}
