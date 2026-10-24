import { normalize } from "./actions_model.js";

export const emptyFilters = () => ({
  tipo: "",
  actividad: "",
  responsable: "",
  compromisoDesde: "",
  compromisoHasta: "",
  estado: "",
  cierreDesde: "",
  cierreHasta: "",
});
export function initialRange(range, now = new Date()) {
  if (range.desde && range.hasta) return { ...range };
  const month = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  return {
    ...range,
    desde: month(new Date(now.getFullYear(), now.getMonth() - 1, 1)),
    hasta: month(now),
  };
}
export function filterKeys(field) {
  if (field === "compromiso") return ["compromisoDesde", "compromisoHasta"];
  if (field === "cierre") return ["cierreDesde", "cierreHasta"];
  return [field];
}
export function rowMatches(d, f) {
  const okTipo = !f.tipo || d.tipo === f.tipo;
  const okActividad =
    !f.actividad || normalize(d.actividad).includes(normalize(f.actividad));
  const okResp = !f.responsable || d.responsable === f.responsable;
  const okEstado = !f.estado || d.estado === f.estado;
  const compromiso = d.compromiso || "",
    cierre = d.cierre || "";
  const okCompDesde =
    !f.compromisoDesde || (compromiso && compromiso >= f.compromisoDesde);
  const okCompHasta =
    !f.compromisoHasta || (compromiso && compromiso <= f.compromisoHasta);
  const okCierreDesde = !f.cierreDesde || (cierre && cierre >= f.cierreDesde);
  const okCierreHasta = !f.cierreHasta || (cierre && cierre <= f.cierreHasta);
  return !!(
    okTipo &&
    okActividad &&
    okResp &&
    okEstado &&
    okCompDesde &&
    okCompHasta &&
    okCierreDesde &&
    okCierreHasta
  );
}
export function filterOptions(rows, field) {
  return [
    ...new Set(
      field === "responsable"
        ? rows.map((x) => x.responsable || "Sin responsable")
        : rows.map((x) => x.tipo).filter(Boolean),
    ),
  ].sort();
}
