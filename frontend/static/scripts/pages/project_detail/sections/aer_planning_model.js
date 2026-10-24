// Original capacity and import rules, extracted without changing their behavior.
export const today = () => new Date().toISOString().slice(0, 10);
export const PLAN_STATES = [
  "En progreso",
  "Completado",
  "Por iniciar",
  "Por validar",
  "Detenido",
];
export const DEPENDENCY_STATES = ["Abierta", "Detenida", "Resuelta"];

export function resources(dashboard) {
  const vals = [];
  ((dashboard && dashboard.detalleRecursos) || []).forEach((x) =>
    vals.push(x.recurso),
  );
  (((dashboard || {}).plan || {}).filas || []).forEach((x) =>
    vals.push(x.responsable),
  );
  (((dashboard || {}).vacaciones || {}).filas || []).forEach((x) =>
    vals.push(x.recurso),
  );
  (((dashboard || {}).evaluaciones || {}).filas || []).forEach((x) =>
    vals.push(x.recurso),
  );
  return [
    ...new Set(
      vals
        .map((x) => String(x || "").trim())
        .filter((x) => x && !/^pendiente$/i.test(x)),
    ),
  ].sort((a, b) => a.localeCompare(b));
}

export function consumesCapacity(x, fechaIso) {
  if (!x) return false;
  const tipo = String(x.tipo || "").toLowerCase();
  const estado = String(x.estado || "").toLowerCase();
  const resp = String(x.responsable || "").trim();
  const esfuerzo = Number(x.esfuerzo != null ? x.esfuerzo : x.orden || 0);
  if (!resp || /^pendiente$/i.test(resp) || tipo === "hito" || esfuerzo <= 0)
    return false;
  if (/complet|cerr|por validar|detenido/.test(estado) || x.finReal)
    return false;
  if (x.inicioPlan && fechaIso && x.inicioPlan > fechaIso) return false;
  // Si ya venció pero sigue abierta, continúa ocupando capacidad hasta cerrarse.
  return true;
}

export function occupancy(filas, hoy = today()) {
  const nombres = [
    ...new Set(
      (filas || [])
        .map((x) => String(x.responsable || "").trim())
        .filter((x) => x && !/^pendiente$/i.test(x)),
    ),
  ];
  const map = {};
  nombres.forEach((n) => (map[n] = { puntos: 0, actividades: [] }));
  (filas || []).forEach((x) => {
    if (!consumesCapacity(x, hoy)) return;
    const n = String(x.responsable || "").trim();
    if (!map[n]) map[n] = { puntos: 0, actividades: [] };
    const e = Number(x.esfuerzo != null ? x.esfuerzo : x.orden || 0);
    map[n].puntos += e;
    map[n].actividades.push(x);
  });
  return map;
}

export function capacity(
  dashboard,
  responsable,
  inicio,
  fin,
  excluirUid = "",
  puntosNuevo = 0,
  estadoNuevo = "En progreso",
  tipoNuevo = "Actividad",
  hoy = today(),
) {
  responsable = String(responsable || "").trim();
  if (!responsable || /^pendiente$/i.test(responsable))
    return { max: 0, actual: 0 };
  const filas = ((dashboard && dashboard.plan) || {}).filas || [];
  const eventos = {};
  const addEvt = (d, v) => {
    if (!d) return;
    eventos[d] = (eventos[d] || 0) + v;
  };
  const addOneDay = (iso) => {
    const d = new Date(iso + "T12:00:00");
    d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 10);
  };
  const normalizaRango = (x) => {
    let ini = x.inicioPlan || hoy;
    let fin = x.finPlan || ini;
    // Una actividad abierta vencida sigue ocupando al menos hasta hoy.
    if (fin < hoy) fin = hoy;
    return [ini, fin];
  };

  filas.forEach((x) => {
    if (x.uid === excluirUid) return;
    if (String(x.responsable || "").trim() !== responsable) return;
    if (String(x.tipo || "").toLowerCase() === "hito") return;
    if (
      /complet|cerr|por validar|detenido/i.test(String(x.estado || "")) ||
      x.finReal
    )
      return;
    const e = Number(x.esfuerzo != null ? x.esfuerzo : x.orden || 0);
    if (e <= 0) return;
    const [ini, fn] = normalizaRango(x);
    addEvt(ini, e);
    addEvt(addOneDay(fn), -e);
  });

  const nuevoActivo =
    !/complet|cerr|por validar|detenido/i.test(String(estadoNuevo || "")) &&
    String(tipoNuevo || "").toLowerCase() !== "hito" &&
    Number(puntosNuevo || 0) > 0;

  if (nuevoActivo) {
    let ini = inicio || hoy;
    let fn = fin || ini;
    if (fn < hoy && /en progreso/i.test(String(estadoNuevo || ""))) fn = hoy;
    addEvt(ini, Number(puntosNuevo || 0));
    addEvt(addOneDay(fn), -Number(puntosNuevo || 0));
  }

  let cur = 0,
    max = 0,
    actual = 0;
  Object.keys(eventos)
    .sort()
    .forEach((d) => {
      cur += eventos[d];
      max = Math.max(max, cur);
      if (d <= hoy) actual = cur;
    });
  return { max, actual };
}

export function normalizeImportDate(v, project = {}, now = new Date()) {
  const s = String(v || "").trim();
  if (!s) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  let m = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
  if (m)
    return `${m[3]}-${String(m[2]).padStart(2, "0")}-${String(m[1]).padStart(2, "0")}`;
  m = s.match(/^(\d{1,2})[\/\-](\d{1,2})$/);
  if (m) {
    const p = project;
    const ref = String(p.fechaInicio || p.fechaFin || "");
    const y = (ref.match(/^(\d{4})/) || [])[1] || String(now.getFullYear());
    return `${y}-${String(m[2]).padStart(2, "0")}-${String(m[1]).padStart(2, "0")}`;
  }
  return s;
}

function parseLine(line, delim) {
  if (delim === "ESPACIOS")
    return String(line || "")
      .trim()
      .split(/\s{2,}/);
  return String(line || "").split(delim);
}

export function parsePlanText(txt, project = {}) {
  txt = String(txt || "")
    .replace(/\u00a0/g, " ")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .trim();
  if (!txt)
    return { ok: false, error: "Pega o carga datos primero.", items: [] };
  const lines = txt
    .split("\n")
    .map((x) => x.replace(/\s+$/, ""))
    .filter((x) => x.trim());
  if (!lines.length)
    return { ok: false, error: "No se encontraron filas.", items: [] };

  const probe = lines.slice(0, Math.min(5, lines.length)).join("\n");
  let delim = "";
  if (probe.includes("\t")) delim = "\t";
  else if (lines[0].includes(";")) delim = ";";
  else if (lines[0].includes(",")) delim = ",";
  else if (/\s{2,}/.test(lines[0])) delim = "ESPACIOS";
  else
    return {
      ok: false,
      error:
        "No pude detectar columnas. Pega directamente desde Excel/Sheets para conservar tabuladores.",
      items: [],
    };

  const cols = [
    "Tipo",
    "Actividad",
    "Responsable",
    "Inicio_Plan",
    "Fin_Plan",
    "Inicio_Real",
    "Fin_Real",
    "Avance",
    "Estado",
    "Dependencia",
    "Notas",
  ];
  const first = parseLine(lines[0], delim).map((x) => String(x || "").trim());
  const header = first.some((x) =>
    /^(tipo|actividad|responsable|inicio_plan|fin_plan|avance|estado)$/i.test(
      x,
    ),
  );
  const start = header ? 1 : 0;
  const items = [];
  const errores = [];

  lines.slice(start).forEach((line, idx) => {
    const a = parseLine(line, delim);
    // Con TSV/CSV conservamos celdas vacías. Con espacios múltiples sólo
    // es un fallback y no puede reconstruir columnas vacías perfectamente.
    const o = { Orden: idx + 1 };
    cols.forEach((c, j) => (o[c] = String(a[j] == null ? "" : a[j]).trim()));
    if (!o.Actividad) {
      errores.push(`Fila ${idx + 1 + start}: sin Actividad`);
      return;
    }
    o.Tipo = o.Tipo || "Actividad";
    o.Inicio_Plan = normalizeImportDate(o.Inicio_Plan, project);
    o.Fin_Plan = normalizeImportDate(o.Fin_Plan, project);
    o.Inicio_Real = normalizeImportDate(o.Inicio_Real, project);
    o.Fin_Real = normalizeImportDate(o.Fin_Real, project);
    if (o.Avance === "") o.Avance = "0";
    if (!o.Estado)
      o.Estado = Number(o.Avance || 0) >= 100 ? "Completado" : "Pendiente";
    items.push(o);
  });

  if (!items.length)
    return {
      ok: false,
      error:
        "No pude construir ninguna actividad. Revisa que las columnas estén separadas por TAB, ; o ,.",
      items: [],
      errores,
    };
  return { ok: true, items, errores, delim, header };
}
