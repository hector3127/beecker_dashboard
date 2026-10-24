import { normalize } from "./actions_model.js";
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

const monthValue = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
export function planningModel(dashboard, range = {}, now = new Date()) {
  range = { ...range };
  if (!range.desde || !range.hasta) {
    range.desde = monthValue(
      new Date(now.getFullYear(), now.getMonth() - 1, 1),
    );
    range.hasta = monthValue(now);
  }
  const pl = dashboard.plan || {},
    filas = (pl.filas || []).slice();
  const fromMonth = range.desde || monthValue(now);
  const toMonth = range.hasta || fromMonth;
  const parseMonthStart = (m) => {
    const [y, mo] = String(m || "")
      .split("-")
      .map(Number);
    return new Date(y || now.getFullYear(), (mo || 1) - 1, 1, 12);
  };
  const monthEnd = (m) => {
    const [y, mo] = String(m || "")
      .split("-")
      .map(Number);
    return new Date(y || now.getFullYear(), mo || 1, 0, 12);
  };
  let min = parseMonthStart(fromMonth);
  let max = monthEnd(toMonth);
  if (max < min) {
    const t = min;
    min = max;
    max = t;
  }

  const spanDays = Math.max(1, Math.round((max - min) / 86400000) + 1);
  const pos = (v) => {
    if (!v) return null;
    const d = new Date(v + "T12:00:00");
    return Math.max(0, Math.min(100, ((d - min) / 86400000 / spanDays) * 100));
  };
  const width = (a, b) => {
    const pa = pos(a),
      pb = pos(b || a);
    if (pa == null || pb == null) return 0.8;
    return Math.max(0.8, pb - pa);
  };
  const fmtShort = (v) => {
    if (!v) return "—";
    const d = new Date(v + "T12:00:00");
    return isNaN(d)
      ? "—"
      : d.toLocaleDateString("es-MX", { day: "numeric", month: "short" });
  };
  const addDays = (d, n) => new Date(d.getTime() + n * 86400000);
  const hoyIso = now.toISOString().slice(0, 10);

  const grouped = [],
    map = {};
  filas.forEach((x) => {
    const key = (x.responsable || "Pendiente").trim() || "Pendiente";
    if (!map[key]) {
      map[key] = { responsable: key, items: [] };
      grouped.push(map[key]);
    }
    map[key].items.push(x);
  });
  grouped.forEach((g) =>
    g.items.sort(
      (a, b) =>
        String(a.inicioPlan || a.finPlan || "").localeCompare(
          String(b.inicioPlan || b.finPlan || ""),
        ) || String(a.actividad || "").localeCompare(String(b.actividad || "")),
    ),
  );

  const monthMap = [];
  let cursor = new Date(min.getFullYear(), min.getMonth(), 1, 12);
  while (cursor <= max) {
    const startM = new Date(cursor.getTime());
    const next = new Date(startM.getFullYear(), startM.getMonth() + 1, 1, 12);
    const left = pos(startM.toISOString().slice(0, 10)) || 0;
    const right = pos(addDays(next, -1).toISOString().slice(0, 10)) || 100;
    monthMap.push({
      label: startM
        .toLocaleDateString("es-MX", { month: "long" })
        .toUpperCase(),
      center: left + (right - left) / 2,
    });
    cursor = next;
  }

  const weeks = [];
  let wk = new Date(min.getTime());
  while (wk <= max) {
    weeks.push({
      date: new Date(wk.getTime()),
      left: pos(wk.toISOString().slice(0, 10)) || 0,
    });
    wk = addDays(wk, 7);
  }

  const todayPos = pos(hoyIso);
  const estadoCompromiso = (x) => {
    const estado = String(x.estado || "").toLowerCase();
    if (/complet|cerr/.test(estado) || !!x.finReal) return "closed";
    if (/detenido|paus/.test(estado)) return "stopped";
    if (/por validar/.test(estado)) return "review";
    if (x.finPlan && x.finPlan === hoyIso) return "duetoday";
    if (x.finPlan && x.finPlan < hoyIso) return "overdue";
    if (/por iniciar/.test(estado) || (x.inicioPlan && x.inicioPlan > hoyIso))
      return "future";
    return "open";
  };

  const total = Number(
    pl.compromisosTotal || filas.filter((x) => x.finPlan).length || 0,
  );
  const cerrados = Number(pl.cerradosTotal || 0);
  const atiempo = Number(pl.cerradosATiempo || 0);
  const vencidos = Number(pl.vencidosAbiertos || 0);
  const vencenHoy = Number(pl.vencenHoy || 0);
  const proximos = (pl.proximosCompromisos || []).slice(0, 6);

  const addIsoDays = (iso, n) => {
    const d = new Date(iso + "T12:00:00");
    d.setDate(d.getDate() + n);
    return d.toISOString().slice(0, 10);
  };
  const vacaciones = (((dashboard || {}).vacaciones || {}).filas || []).slice();
  const limite7 = addIsoDays(hoyIso, 7);
  const limite30Vac = addIsoDays(hoyIso, 30);
  const vacacionesProximas = vacaciones
    .filter(
      (v) =>
        !/cancel|rechaz/i.test(String(v.estado || "")) &&
        v.fin >= hoyIso &&
        v.inicio <= limite30Vac,
    )
    .sort((a, b) => String(a.inicio).localeCompare(String(b.inicio)));
  const diasHabiles = (a, b) => {
    if (!a || !b || b < a) return 0;
    let d = new Date(a + "T12:00:00"),
      f = new Date(b + "T12:00:00"),
      n = 0;
    while (d <= f) {
      if (d.getDay() !== 0 && d.getDay() !== 6) n++;
      d.setDate(d.getDate() + 1);
    }
    return n;
  };
  const habiles30 = Math.max(1, diasHabiles(hoyIso, limite30Vac));
  const vacDiasPorRecurso = {};
  vacacionesProximas.forEach((v) => {
    const a = v.inicio < hoyIso ? hoyIso : v.inicio,
      b = v.fin > limite30Vac ? limite30Vac : v.fin;
    vacDiasPorRecurso[v.recurso] =
      (vacDiasPorRecurso[v.recurso] || 0) + diasHabiles(a, b);
  });
  const vacWeeks = Array.from({ length: 6 }, (_, i) => {
    const ini = addIsoDays(hoyIso, i * 7);
    const fin = addIsoDays(ini, 6);
    const ausentes = new Set(
      vacaciones
        .filter(
          (v) =>
            !/cancel|rechaz/i.test(String(v.estado || "")) &&
            v.inicio <= fin &&
            v.fin >= ini,
        )
        .map((v) => v.recurso),
    );
    return { ini, fin, count: ausentes.size };
  });
  const abiertos = filas.filter(
    (x) => !(/complet|cerr/i.test(String(x.estado || "")) || x.finReal),
  );
  const proximos7 = abiertos
    .filter(
      (x) =>
        x.finPlan &&
        x.finPlan >= hoyIso &&
        x.finPlan <= limite7 &&
        !/por validar|detenido/i.test(String(x.estado || "")),
    )
    .sort((a, b) => String(a.finPlan).localeCompare(String(b.finPlan)));
  const hitosValidar = filas.filter(
    (x) =>
      String(x.tipo || "").toLowerCase() === "hito" &&
      /por validar/i.test(String(x.estado || "")),
  );
  const vencidosRows = abiertos
    .filter(
      (x) =>
        x.finPlan &&
        x.finPlan < hoyIso &&
        !/por validar|detenido/i.test(String(x.estado || "")),
    )
    .sort((a, b) => String(a.finPlan).localeCompare(String(b.finPlan)));
  const detenidosRows = abiertos.filter((x) =>
    /detenido/i.test(String(x.estado || "")),
  );
  const depsRows = filas.filter((x) => String(x.dependencia || "").trim());
  const depStatus = (x) => {
    const e = String(x.estadoDependencia || "Abierta").toLowerCase();
    if (e.includes("resuelt")) return "Resuelta";
    if (e.includes("deten")) return "Detenida";
    if (
      x.finPlan &&
      x.finPlan < hoyIso &&
      !(/complet|cerr/i.test(String(x.estado || "")) || x.finReal)
    )
      return "Vencida";
    return "Abierta";
  };
  const esfuerzoPlan = filas.reduce(
    (s, x) => s + Number(x.esfuerzo != null ? x.esfuerzo : x.orden || 0),
    0,
  );
  const esfuerzoCerrado = filas
    .filter((x) => /complet|cerr/i.test(String(x.estado || "")) || x.finReal)
    .reduce(
      (s, x) => s + Number(x.esfuerzo != null ? x.esfuerzo : x.orden || 0),
      0,
    );
  const esfuerzoPendiente = Math.max(0, esfuerzoPlan - esfuerzoCerrado);
  const avancePct = total ? Math.round((cerrados / total) * 100) : 0;

  // Capacidad ACTUAL: 6 puntos = 100% por recurso.
  // Solo consume capacidad una actividad/hora asignada que ya inició y sigue abierta.
  // Completado, Por validar, Detenido e Hito no consumen capacidad.
  const ocupacionActual = occupancy(filas, hoyIso);
  const respRows = Object.entries(ocupacionActual)
    .sort((a, b) => b[1].puntos - a[1].puntos || a[0].localeCompare(b[0]))
    .slice(0, 8);
  const recursosConCap = respRows.length;
  const puntosOcupados = respRows.reduce(
    (s, [, v]) => s + Number(v.puntos || 0),
    0,
  );
  const capacidadTotal = recursosConCap * 6;
  const puntosDisponibles = respRows.reduce(
    (s, [, v]) => s + Math.max(0, 6 - Number(v.puntos || 0)),
    0,
  );
  const recursosOcupados = respRows.filter(
    ([, v]) => Number(v.puntos || 0) === 6,
  ).length;
  const recursosSobrecargados = respRows.filter(
    ([, v]) => Number(v.puntos || 0) > 6,
  ).length;
  const depGroups = {};
  const depPriority = { Detenida: 4, Vencida: 3, Abierta: 2, Resuelta: 1 };
  depsRows.forEach((x) => {
    const key = normalize(x.dependencia);
    if (!key) return;
    const st = depStatus(x);
    if (!depGroups[key])
      depGroups[key] = { dependencia: x.dependencia, status: st, rows: [x] };
    else {
      depGroups[key].rows.push(x);
      if ((depPriority[st] || 0) > (depPriority[depGroups[key].status] || 0))
        depGroups[key].status = st;
    }
  });
  const depUnique = Object.values(depGroups);
  const depVencidas = depUnique.filter((x) => x.status === "Vencida").length;
  const depAbiertas = depUnique.filter((x) => x.status === "Abierta").length;
  const depDetenidas = depUnique.filter((x) => x.status === "Detenida").length;
  const capAlertas = respRows.filter(([, v]) => Number(v.puntos || 0) >= 6);
  const capSobrecarga = capAlertas.filter(([, v]) => Number(v.puntos || 0) > 6);
  const bloqueosCriticos = depDetenidas;
  const attnCount =
    vencidosRows.length +
    proximos7.length +
    hitosValidar.length +
    bloqueosCriticos;

  return {
    pl,
    filas,
    fromMonth,
    toMonth,
    min,
    max,
    spanDays,
    pos,
    width,
    fmtShort,
    hoyIso,
    grouped,
    monthMap,
    weeks,
    todayPos,
    estadoCompromiso,
    total,
    cerrados,
    atiempo,
    vencidos,
    vencenHoy,
    proximos,
    vacaciones,
    vacacionesProximas,
    habiles30,
    vacDiasPorRecurso,
    vacWeeks,
    proximos7,
    hitosValidar,
    vencidosRows,
    detenidosRows,
    depStatus,
    esfuerzoPlan,
    esfuerzoCerrado,
    esfuerzoPendiente,
    avancePct,
    ocupacionActual,
    respRows,
    recursosConCap,
    puntosOcupados,
    capacidadTotal,
    puntosDisponibles,
    recursosOcupados,
    recursosSobrecargados,
    depUnique,
    depVencidas,
    depAbiertas,
    depDetenidas,
    bloqueosCriticos,
    attnCount,
  };
}
