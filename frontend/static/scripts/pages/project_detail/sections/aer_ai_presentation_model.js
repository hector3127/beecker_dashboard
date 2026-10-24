import { facts } from "./aer_ai_model.js";
const escape = (v) =>
  String(v == null ? "" : v)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
export function memoryDate(stamp) {
  const value = String(stamp || "").trim();
  const m = value.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
  return m
    ? m[3] + "/" + m[2] + "/" + m[1] + " a las " + m[4] + ":" + m[5]
    : value;
}
export function summaryMarkup(texto) {
  return escape(String(texto || ""))
    .replace(/^\*\*\*([^\n*]+)\*\*\*\s*$/gm, "<strong>$1</strong>")
    .replace(/\*\*([^\n*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/^[-•] /gm, "&bull; ")
    .replace(/\n/g, "<br>");
}
export function minuteSummary(contenido) {
  const raw = String(contenido || "")
    .replace(/\r\n?/g, "\n")
    .trim();
  if (!raw) return "";
  const pattern =
    /(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*\*|__)?\s*(?:RESUMEN(?:\s+(?:DE\s+LA\s+MINUTA|GENERAL))?|RESUMEN\s+DE\s+LA\s+REUNI[ÓO]N)\s*:?\s*(?:\*\*|__)?\s*/i;
  let m = pattern.exec(raw),
    found = "";
  if (m) {
    let next = raw.slice(m.index + m[0].length);
    // Cortar antes de la siguiente sección, no antes de bullets normales.
    const end = next.search(
      /\n\s*(?:#{1,4}\s+|(?:\*\*|__)\s*(?:PENDIENTES|ACUERDOS|AVANCE|ESTADO|PUNTOS DE ATENCI[ÓO]N|GENERALES|NOTA|RESPONSABLES|PR[ÓO]XIMOS PASOS)[^\n]{0,70}(?:\*\*|__)?\s*:?)\s*\n/i,
    );
    if (end >= 0) next = next.slice(0, end);
    found = next.trim();
  }
  // Formato de reporte nuevo sin bloque RESUMEN: usar el bloque Estado/Avance.
  if (!found) {
    const stage =
      /(?:^|\n)\s*(?:#{1,4}\s*)?(?:📊\s*)?(?:\*\*|__)?\s*(?:AVANCE\s*\/\s*ESTADO ACTUAL|ESTADO GENERAL)\s*(?:\*\*|__)?\s*:?/i.exec(
        raw,
      );
    if (stage) {
      let rest = raw.slice(stage.index + stage[0].length);
      const stop = rest.search(
        /\n\s*(?:⚠️?|📍|📌|#{1,4}\s*(?:PUNTOS DE ATENCI[ÓO]N|GENERALES|PENDIENTES))/i,
      );
      if (stop >= 0) rest = rest.slice(0, stop);
      found = rest.trim();
    }
  }
  // Minutas antiguas sin encabezado de resumen: SOLO vista previa, sin inventar información.
  if (!found)
    found = raw.replace(/^\s*(?:#{1,4}\s*)?\*\*MINUTA[^\n]*\n?/i, "").trim();
  return found.length > 440 ? found.slice(0, 437).trimEnd() + "…" : found;
}
export function presentation(dashboard, state, now = new Date()) {
  const f = facts(dashboard, state, now),
    s = state,
    anal = s.analisis && s.analisis.analisis;
  const mins = s.minutas || [],
    k = f.c.k;
  const memoria = s.analisis && s.analisis.guardadoEn,
    tz = s.analisis && s.analisis.zonaHoraria;
  const resumen = anal
    ? anal.resumen
    : f.alerts.length
      ? f.alerts.slice(0, 4)
      : ["Sin alertas automáticas con los datos cargados."];
  const recs = anal ? anal.recomendaciones : [];
  const dim =
    k.consumoPct > 100 ? Math.max(0, 100 - (k.consumoPct - 100)) : 100;
  return { f, s, anal, mins, k, memoria, tz, resumen, recs, dim };
}
