import { phases, dateMs } from "./ixs_executive_model.js";
const escape = (v) =>
  String(v == null ? "" : v)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
export function stage(data, now = new Date()) {
  if ((data || {}).cerrado) return { texto: "Cerrado", clase: "green" };
  const fases = phases(data || {});
  const susp = Array.isArray((data || {}).suspensiones)
    ? data.suspensiones
    : [];
  const hoy = new Date(now);
  hoy.setHours(0, 0, 0, 0);
  const hoyMs = hoy.getTime();
  const inRange = (ms, a, b) =>
    Number.isFinite(ms) &&
    Number.isFinite(a) &&
    Number.isFinite(b) &&
    ms >= Math.min(a, b) &&
    ms <= Math.max(a, b);
  const suspActiva = susp.some((s) => {
    const ini = dateMs(s.fechaInicio),
      fin = dateMs(s.fechaFin || s.fechaInicio);
    return inRange(hoyMs, ini, fin);
  });
  if (suspActiva) return { texto: "Suspendido", clase: "orange" };

  const activa = fases.find((f) => {
    const ini = dateMs(f.start),
      fin = dateMs(f.end || f.start);
    return !!f.active || inRange(hoyMs, ini, fin);
  });
  if (activa) return { texto: escape(activa.name || "En progreso"), clase: "" };

  const futuras = (data && Array.isArray(data.hitos) ? data.hitos : [])
    .filter(
      (h) =>
        Number.isFinite(dateMs(h.fechaInicioPlan)) &&
        dateMs(h.fechaInicioPlan) >= hoyMs,
    )
    .sort((a, b) => dateMs(a.fechaInicioPlan) - dateMs(b.fechaInicioPlan));
  if (futuras.length)
    return { texto: escape(futuras[0].nombre || "Pendiente"), clase: "" };

  if (fases.length) {
    const ultima = fases.slice().sort((a, b) => {
      const af = dateMs(a.end || a.start),
        bf = dateMs(b.end || b.start);
      return (
        (Number.isFinite(bf) ? bf : -Infinity) -
        (Number.isFinite(af) ? af : -Infinity)
      );
    })[0];
    return { texto: escape(ultima.name || "Sin etapa"), clase: "" };
  }

  return { texto: "Sin etapa", clase: "" };
}
export function aerStatus(v) {
  const s = String(v || "").toLowerCase();
  if (/crit|alto|atras|venc|riesgo/.test(s)) return "bad";
  if (/complet|cerr|tiempo|salud/.test(s)) return "ok";
  if (/por iniciar|pend/.test(s)) return "warn";
  if (/detenido|paus/.test(s)) return "warn";
  if (/en progreso|seguimiento|curso|por validar/.test(s)) return "info";
  return "info";
}
