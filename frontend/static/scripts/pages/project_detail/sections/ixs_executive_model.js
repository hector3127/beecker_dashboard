// Original IXS presentation rules, moved without changing calculations.
const EMOJI_REGEX = /\p{Extended_Pictographic}/u;
export function num(n, dec = 1) {
  const v = Number(n);
  return Number.isFinite(v)
    ? v.toLocaleString("es-MX", { maximumFractionDigits: dec })
    : "—";
}

export function pct(n) {
  const v = Number(n);
  return Number.isFinite(v) ? num(v, 1) + "%" : "—";
}

export function limit(n) {
  return Math.min(100, Math.max(0, Number(n) || 0));
}

export function dateText(d) {
  if (!d) return "—";
  const raw = String(d);
  const lat = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (lat)
    return `${lat[1].padStart(2, "0")}/${lat[2].padStart(2, "0")}/${lat[3]}`;
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[3]}/${m[2]}/${m[1]}`;
  const x = new Date(d);
  return isNaN(x.getTime())
    ? "—"
    : x.toLocaleDateString("es-MX", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
}

export function dateMs(d) {
  if (!d) return NaN;
  const lat = String(d).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (lat) return new Date(+lat[3], +lat[2] - 1, +lat[1], 12).getTime();
  const m = String(d).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m
    ? new Date(+m[1], +m[2] - 1, +m[3], 12).getTime()
    : new Date(d).getTime();
}

export function phases(data) {
  const hist = Array.isArray(data.historialCompleto)
    ? data.historialCompleto
    : [];
  const byName = new Map();
  hist
    .filter((x) => x && x.fechaInicio)
    .forEach((h) => {
      const key = String(h.fase || "")
        .trim()
        .toLowerCase();
      if (!key) return;
      if (!byName.has(key))
        byName.set(key, {
          name: h.fase,
          start: h.fechaInicio,
          end: h.fechaFin || h.fechaInicio,
          active: !!h.enCurso,
        });
      else {
        const r = byName.get(key);
        if (dateMs(h.fechaInicio) < dateMs(r.start)) r.start = h.fechaInicio;
        if (dateMs(h.fechaFin || h.fechaInicio) > dateMs(r.end))
          r.end = h.fechaFin || h.fechaInicio;
        if (h.enCurso) r.active = true;
      }
    });
  return Array.from(byName.values()).sort(
    (a, b) => dateMs(a.start) - dateMs(b.start),
  );
}

export function milestones(data) {
  const hist = phases(data);
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const hoyMs = hoy.getTime();
  const principales = (data.hitos || []).map((h) => {
    const match = hist.find(
      (x) =>
        String(x.name || "").toLowerCase() ===
        String(h.nombre || "").toLowerCase(),
    );
    const fin = match ? (match.active ? null : match.end) : h.fechaFinPlan;
    return {
      name: h.nombre || "Fase",
      start: match ? match.start : h.fechaInicioPlan,
      finish: fin || h.fechaFinPlan || h.fechaInicioPlan,
      state: match
        ? match.active
          ? "En curso"
          : dateMs(match.end) < hoyMs
            ? "Completado"
            : "En curso"
        : "Pendiente",
      extra: false,
    };
  });
  const extras = (data.hitosAdicionales || []).map((h) => {
    const cat = milestoneCategory(h.tipo);
    const when = dateMs(h.fecha);
    return {
      name: cleanMilestone(h.tipo) || cat.etiqueta || "Hito",
      start: h.fecha,
      finish: h.fecha,
      state: Number.isFinite(when) && when < hoyMs ? "Completado" : "Pendiente",
      extra: true,
      icon: cat.icono || "📌",
      group: cat.etiqueta || "Hitos adicionales",
      uid: h.indice,
      notes: h.observacion || "",
    };
  });
  return principales.concat(extras).sort((a, b) => {
    const am = dateMs(a.start),
      bm = dateMs(b.start);
    return (
      (Number.isFinite(am) ? am : Infinity) -
      (Number.isFinite(bm) ? bm : Infinity)
    );
  });
}

export function prdDate(data) {
  const isDeployment = (x) =>
    /^deployment(?:\s+(?:est|s\d+))?$/i.test(String(x || "").trim());
  const history = (data.historialCompleto || []).filter(
    (h) => isDeployment(h.fase) && h.fechaFin,
  );
  const plans = (data.hitos || []).filter(
    (h) => isDeployment(h.nombre) && h.fechaFinPlan,
  );
  const latest = (items, key) =>
    items.sort((a, b) => dateMs(b[key]) - dateMs(a[key]))[0];
  return (
    (latest(history, "fechaFin") || {}).fechaFin ||
    (latest(plans, "fechaFinPlan") || {}).fechaFinPlan ||
    ""
  );
}

export function cleanMilestone(tipoCompleto) {
  const nombre = String(tipoCompleto || "").trim();
  const primeraPalabra = nombre.split(" ")[0];
  if (EMOJI_REGEX.test(primeraPalabra))
    return nombre.split(" ").slice(1).join(" ").trim() || nombre;
  return nombre;
}

export function milestoneCategory(tipoCompleto) {
  let nombre = String(tipoCompleto || "").trim();
  const primeraPalabra = nombre.split(" ")[0];
  const teniaEmoji = EMOJI_REGEX.test(primeraPalabra);
  if (teniaEmoji) nombre = nombre.split(" ").slice(1).join(" ").trim();
  const n = nombre.toLowerCase();

  if (n.includes("demo"))
    return { clave: "demo", etiqueta: "Demostraciones", icono: "🎥" };
  if (n.includes("qa"))
    return { clave: "qa", etiqueta: "Pases a QA", icono: "🧪" };
  if (n.includes("prod"))
    return { clave: "prod", etiqueta: "Pases a Producción", icono: "🚀" };
  if (n.includes("uat"))
    return { clave: "uat", etiqueta: "Ejecuciones UAT", icono: "✅" };
  if (n.includes("capacitac") || n.includes("training"))
    return { clave: "train", etiqueta: "Capacitaciones", icono: "🎓" };
  if (n.includes("revis") || n.includes("review"))
    return { clave: "rev", etiqueta: "Revisiones", icono: "🔍" };
  if (n.includes("kickoff") || n.includes("kick off") || n.includes("arranque"))
    return { clave: "kickoff", etiqueta: "Kickoffs", icono: "🏁" };
  if (n.includes("entrega"))
    return { clave: "entrega", etiqueta: "Entregas", icono: "📦" };

  // Sin categoria reconocida: el propio nombre limpio es su categoria,
  // usando el icono que el usuario eligió al crearlo (si lo eligió).
  return {
    clave: n,
    etiqueta: nombre || tipoCompleto,
    icono: teniaEmoji ? primeraPalabra : "📌",
  };
}

export function resourceKey(v) {
  return String(v || "")
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .toLowerCase();
}

export function executiveModel(data) {
  const d = data,
    p = d.proyecto || {},
    av = d.avance || {},
    pr = d.presupuesto || {},
    ke = d.kpisExtra || {},
    rt = d.totalesRecursos || {};
  const mainHitos = milestones(d),
    fechaSalidaPRD = prdDate(d),
    done = mainHitos.filter((h) => !h.extra && h.state === "Completado").length,
    totalMain = mainHitos.filter((h) => !h.extra).length;
  const overResources = (d.filasRecursosCompleto || []).filter(
    (x) =>
      /exced|retras/i.test(String(x.estado || "")) || Number(x.balance) < 0,
  );
  const financial = Number(ke.pctCumplimientoFinanciero);
  const budget = Number(pr.budget) || 0,
    burn = Number(pr.burn) || 0;
  const avancePorHitos =
    av.fuente === "Hitos principales" ||
    av.fuente === "Hitos y fechas de etapa" ||
    av.fuente === "Sin hitos planificados";
  const avancePorFechas = av.fuente === "Hitos y fechas de etapa";
  const avanceDisponible = av.pct != null && Number.isFinite(Number(av.pct));
  const ritmoDisponible =
    av.indiceRitmo != null && Number.isFinite(Number(av.indiceRitmo));
  const consumoDisponible = pr.consumoDisponible !== false;
  const ritmo = ritmoDisponible ? Number(av.indiceRitmo) : null;
  const ritmoTexto =
    ritmo == null
      ? "Sin avance o fechas para calcularlo"
      : avancePorHitos
        ? ritmo < 0.9
          ? "Por debajo del plan"
          : ritmo > 1.1
            ? "Por delante del plan"
            : "En ritmo con el plan"
        : ritmo > 1.1
          ? "Consumo por encima del plan"
          : "Consumo dentro del plan";
  const state = String(p.estadoGeneral || "Sin estado"),
    riskDate = String(p.nivelRiesgoFecha || "Sin dato");
  const riskHigh = /alto/i.test(riskDate),
    riskGeneral = /riesgo|criti/i.test(state);
  const summaries = [];
  if (Number.isFinite(financial) && financial > 100)
    summaries.push([
      "red",
      `El consumo financiero es ${pct(financial)} frente al estimado.`,
    ]);
  else
    summaries.push([
      "green",
      `El cumplimiento financiero registrado es ${pct(financial)}.`,
    ]);
  summaries.push([
    avanceDisponible ? "green" : "amber",
    avanceDisponible
      ? `El ${avancePorFechas ? "avance estimado por fechas de etapa" : avancePorHitos ? "avance por hitos" : "avance registrado"} del proyecto es ${pct(av.pct)}.`
      : "No hay hitos planificados para calcular el avance.",
  ]);
  if (totalMain)
    summaries.push([
      "green",
      `Se han completado ${done} de ${totalMain} fases principales.`,
    ]);
  if (overResources.length)
    summaries.push([
      "amber",
      `${overResources.length} recurso(s) requieren revisar su balance de horas.`,
    ]);
  if (riskHigh)
    summaries.push([
      "red",
      "La fecha de salida del proyecto tiene nivel de riesgo alto.",
    ]);
  if (fechaSalidaPRD)
    summaries.push([
      "green",
      `Fecha de salida a PRD (fin de Deployment): ${dateText(fechaSalidaPRD)}.`,
    ]);
  const attention = [];
  if (financial > 100)
    attention.push({
      color: "red",
      title: "Desvío financiero del proyecto",
      desc: `Consumo ${pct(financial)} frente al estimado.`,
      source: "Finanzas",
    });
  if (
    avancePorHitos &&
    ritmo != null &&
    ritmo < 0.9 &&
    Number(av.pctTiempoTranscurrido) >= 20
  )
    attention.push({
      color: "amber",
      title: "Avance de hitos por debajo del plan",
      desc: `${done} de ${totalMain} hitos completados; ${pct(av.pctTiempoTranscurrido)} del tiempo transcurrido.`,
      source: "Planeación",
    });
  if (overResources.length)
    attention.push({
      color: "amber",
      title: "Revisar carga de trabajo de recursos",
      desc: `${overResources.length} recurso(s) con balance negativo o estado de exceso.`,
      source: "Recursos",
    });
  if (riskHigh)
    attention.push({
      color: "red",
      title: "Riesgo en fecha de salida",
      desc: fechaSalidaPRD
        ? `Fin de Deployment: ${dateText(fechaSalidaPRD)}.`
        : "Revisa la fecha de fin de Deployment en Planeación.",
      source: "Planeación",
    });
  if (!attention.length)
    attention.push({
      color: "green",
      title: "Sin alertas derivadas de estos indicadores",
      desc: "Consulta el detalle de recursos, riesgos y fechas para mantener el seguimiento.",
      source: "Resumen",
    });
  const hoursRows = (d.filasRecursosCompleto || []).map((x) => ({
    nombre: (x.nombre || "") + (x.posicion ? " — " + x.posicion : ""),
    horasReales: x.horasReales,
    horasEstimadas: x.horasEstimadas,
  }));
  const roleRows = (d.porRol || []).map((x) => ({
    nombre: x.rol,
    horasReales: x.horasReales,
    horasEstimadas: x.horasEstimadas,
  }));
  const principalDone = mainHitos.filter(
    (x) => !x.extra && x.state === "Completado",
  );
  const extrasDone = mainHitos.filter(
    (x) => x.extra && x.state === "Completado",
  );
  const todo = mainHitos.filter((x) => x.state !== "Completado");

  return {
    d,
    p,
    av,
    pr,
    ke,
    rt,
    mainHitos,
    fechaSalidaPRD,
    done,
    totalMain,
    overResources,
    financial,
    budget,
    burn,
    avancePorHitos,
    avancePorFechas,
    avanceDisponible,
    ritmoDisponible,
    consumoDisponible,
    ritmo,
    ritmoTexto,
    state,
    riskDate,
    riskHigh,
    riskGeneral,
    summaries,
    attention,
    hoursRows,
    roleRows,
    principalDone,
    extrasDone,
    todo,
  };
}

export function timelineModel(data) {
  const plan = (data.hitos || [])
    .filter((x) => x.fechaInicioPlan && x.fechaFinPlan)
    .map((x) => ({
      name: x.nombre + " EST",
      from: x.fechaInicioPlan,
      to: x.fechaFinPlan,
      type: "plan",
    }));
  const real = phases(data).map((x) => ({
    name: x.name,
    from: x.start,
    to: x.active ? new Date() : x.end,
    type: "real",
    active: x.active,
    markers: [],
  }));
  const holds = (data.suspensiones || [])
    .filter((x) => x.fechaInicio)
    .map((x) => ({
      name: "Suspendido",
      from: x.fechaInicio,
      to: x.fechaFin || new Date(),
      type: "hold",
    }));
  const markers = (data.hitosAdicionales || [])
    .map((h, sourceIndex) => {
      const time = dateMs(h.fecha);
      if (!Number.isFinite(time)) return null;
      const cat = milestoneCategory(h.tipo);
      return {
        sourceIndex: sourceIndex,
        time: time,
        icon: cat.icono || "📌",
        cls: ["demo", "qa", "prod", "uat"].includes(cat.clave)
          ? cat.clave
          : "other",
        label: cleanMilestone(h.tipo) || cat.etiqueta || "Evento",
        group: cat.etiqueta || "Otros",
        date: h.fecha,
      };
    })
    .filter(Boolean);
  const rows = plan.concat(real, holds);
  const times = rows
    .flatMap((x) => [dateMs(x.from), dateMs(x.to)])
    .concat(markers.map((x) => x.time))
    .filter(Number.isFinite);
  if (!times.length) return null;
  const now = Date.now();
  times.push(now);
  const day = 864e5,
    min = Math.min(...times) - day * 3,
    max = Math.max(...times) + day * 3,
    range = Math.max(day, max - min);
  const pos = (date) => ((dateMs(date) - min) / range) * 100;
  // Cada evento se asigna a la etapa real que contiene su fecha; de no
  // coincidir con ninguna etapa, a la barra real más cercana por intervalo.
  markers.forEach((m) => {
    let chosen = null,
      dist = Infinity;
    real.forEach((r) => {
      const a = dateMs(r.from),
        b = r.active ? now : dateMs(r.to);
      if (!Number.isFinite(a) || !Number.isFinite(b)) return;
      const lo = Math.min(a, b),
        hi = Math.max(a, b);
      const distance =
        m.time < lo ? lo - m.time : m.time > hi ? m.time - hi : 0;
      if (distance < dist) {
        dist = distance;
        chosen = r;
      }
    });
    if (chosen) chosen.markers.push(m);
  });
  // Cuando no existe una fase real, mantener visibles los hitos en una fila.
  const loneMarkers = real.length ? [] : markers;

  return { plan, real, holds, markers, loneMarkers, min, max, range, pos };
}
