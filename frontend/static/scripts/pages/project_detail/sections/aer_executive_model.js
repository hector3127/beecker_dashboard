// Original presentation rules, moved unchanged from the renderer.
export function hours(n) {
  return `${(Math.round(Number(n || 0) * 100) / 100).toLocaleString("es-MX")} h`;
}

export function formatDate(v) {
  if (!v) return "—";
  const m = String(v).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : String(v);
}

export function clamp(n) {
  return Math.max(0, Math.min(100, Number(n || 0)));
}

export function dimensions(d) {
  const k = (d && d.kpis) || {};
  const r = (d && d.riesgos) || {};
  const backend = k.healthDimensiones || {};
  const fuentes = k.healthFuentes || {};

  // Compatibilidad: si el frontend nuevo está hablando con el service viejo,
  // healthDimensiones no existe. Calculamos las dimensiones automáticas para
  // que la UI no muestre 0% falsos.
  let esfuerzo = backend.esfuerzo;
  if (esfuerzo == null) {
    esfuerzo = 100;
    if (Number(k.consumoPct || 0) > 100)
      esfuerzo -= Math.min(40, (Number(k.consumoPct) - 100) * 0.7 + 15);
    else if (Number(k.desviacionPts || 0) > 10)
      esfuerzo -= Math.min(30, Number(k.desviacionPts) * 0.8);
    if (Number(k.pctNoFacturables || 0) > 20)
      esfuerzo -= Math.min(15, (Number(k.pctNoFacturables) - 20) * 0.5 + 5);
    if (Number(k.pctFueraHorario || 0) > 5)
      esfuerzo -= Math.min(15, (Number(k.pctFueraHorario) - 5) * 0.8 + 4);
    esfuerzo = Math.max(0, Math.min(100, Math.round(esfuerzo)));
  }

  let tiempo = backend.tiempo;
  if (tiempo == null) {
    const dr = k.diasRestantes;
    tiempo = dr == null ? 100 : dr < 0 ? 40 : dr <= 14 ? 75 : 100;
  }

  let costo = backend.costo;
  if (costo == null)
    costo = Math.max(
      0,
      Math.min(100, 100 - Math.max(0, Number(k.consumoPct || 0) - 100)),
    );

  let riesgo = backend.riesgo;
  const tieneRiesgos = (r.filas && r.filas.length) || fuentes.riesgo === true;
  if (!tieneRiesgos) riesgo = null;
  else if (riesgo == null) riesgo = Number(r.score == null ? 100 : r.score);

  return { tiempo, esfuerzo, costo: Math.round(costo), riesgo };
}

export function executiveModel(data, now = new Date()) {
  const d = data || {},
    p = d.proyecto || {},
    k = d.kpis || {},
    pl = d.plan || {},
    r = d.riesgos || {},
    ac = d.acciones || {};
  const dims = dimensions(d);
  const hoyIso = now.toISOString().slice(0, 10);
  const filas = (pl.filas || []).slice();
  const total = Number(
    pl.compromisosTotal || filas.filter((x) => x.finPlan).length || 0,
  );
  const cerrados = Number(
    pl.cerradosTotal ||
      filas.filter(
        (x) => /complet|cerr/i.test(String(x.estado || "")) || x.finReal,
      ).length ||
      0,
  );
  const pctCerrados = Number(
    pl.pctCerrados || (total ? Math.round((cerrados / total) * 1000) / 10 : 0),
  );
  const pctATiempo = Number(pl.pctCerradosATiempo || 0);
  const vencidos = Number(pl.vencidosAbiertos || 0);
  const vencenHoy = Number(pl.vencenHoy || 0);
  const criticos = (r.criticos || []).length;
  const abiertosRiesgo = (r.activos || []).length;
  const isClosed = (x) =>
    /complet|cerr/i.test(String((x && x.estado) || "")) || !!(x && x.finReal);
  const isStopped = (x) => /deten|paus/i.test(String((x && x.estado) || ""));
  const isReview = (x) => /por validar/i.test(String((x && x.estado) || ""));

  const orderedPlan = filas
    .slice()
    .sort(
      (a, b) =>
        String(a.finPlan || "9999-12-31").localeCompare(
          String(b.finPlan || "9999-12-31"),
        ) || String(a.actividad || "").localeCompare(String(b.actividad || "")),
    );
  const nextItems = orderedPlan.filter(
    (x) => x.finPlan && x.finPlan >= hoyIso && !isClosed(x),
  );
  const nextMilestone = nextItems[0] || null;
  const nextMilestoneDate = nextMilestone ? nextMilestone.finPlan : null;
  const nextMilestoneCount = nextItems.length;

  const durationPct = (() => {
    if (!p.fechaInicio || !p.fechaFin) return null;
    const ini = new Date(p.fechaInicio + "T12:00:00");
    const fin = new Date(p.fechaFin + "T12:00:00");
    const hoy = new Date(hoyIso + "T12:00:00");
    if (isNaN(ini) || isNaN(fin) || fin <= ini) return null;
    return clamp(((hoy - ini) / (fin - ini)) * 100);
  })();
  const tiempoVsPlan =
    dims.tiempo == null
      ? durationPct == null
        ? 0
        : Math.round(durationPct)
      : Math.round(dims.tiempo);
  const presupuestoPct = clamp(Number(k.consumoPct || 0));
  const costoReal = Number(k.costoReal || 0);

  const depRows = filas.filter((x) => String(x.dependencia || "").trim());
  const depPriority = { Detenida: 4, Vencida: 3, Abierta: 2, Resuelta: 1 };
  const depGroups = {};
  const depStatus = (x) => {
    const e = String(x.estadoDependencia || "Abierta").toLowerCase();
    if (e.includes("resuelt")) return "Resuelta";
    if (e.includes("deten")) return "Detenida";
    if (x.finPlan && x.finPlan < hoyIso && !isClosed(x)) return "Vencida";
    return "Abierta";
  };
  depRows.forEach((x) => {
    const key = String(x.dependencia || "")
      .trim()
      .toLowerCase();
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
  const bloqueos =
    depDetenidas + filas.filter((x) => isStopped(x) && !isClosed(x)).length;

  const healthScore = Number(k.healthScore || 0);
  const badgeText =
    healthScore >= 85
      ? "Proyecto en control con puntos de atención"
      : healthScore >= 70
        ? "Proyecto estable con focos de seguimiento"
        : "Proyecto en alerta ejecutiva";

  const attn = [];
  const addAttn = (cls, title, detail, source, responsable, fecha) =>
    attn.push({ cls, title, detail, source, responsable, fecha });
  orderedPlan
    .filter(
      (x) =>
        x.finPlan &&
        x.finPlan < hoyIso &&
        !isClosed(x) &&
        !isReview(x) &&
        !isStopped(x),
    )
    .slice(0, 2)
    .forEach((x) =>
      addAttn(
        "red",
        x.actividad,
        "Vencido",
        "Planeación",
        x.responsable,
        x.finPlan,
      ),
    );
  (ac.vencidas || [])
    .slice(0, 2)
    .forEach((x) =>
      addAttn(
        "red",
        x.accion || "Acción vencida",
        x.notas || "Requiere seguimiento inmediato",
        "Acciones",
        x.responsable,
        x.fechaLimite,
      ),
    );
  (r.criticos || [])
    .slice(0, 1)
    .forEach((x) =>
      addAttn(
        "red",
        x.riesgo,
        "Riesgo crítico",
        "Riesgos",
        x.responsable,
        x.fechaLimite,
      ),
    );
  orderedPlan
    .filter(
      (x) =>
        x.finPlan &&
        x.finPlan === hoyIso &&
        !isClosed(x) &&
        !isReview(x) &&
        !isStopped(x),
    )
    .slice(0, 2)
    .forEach((x) =>
      addAttn(
        "orange",
        x.actividad,
        "Vence hoy",
        "Planeación",
        x.responsable,
        x.finPlan,
      ),
    );
  nextItems
    .filter((x) => x.finPlan && x.finPlan > hoyIso)
    .slice(0, 2)
    .forEach((x) =>
      addAttn(
        "purple",
        x.actividad,
        "Próximo hito",
        "Planeación",
        x.responsable,
        x.finPlan,
      ),
    );
  if (!attn.length)
    addAttn(
      "purple",
      "Sin alertas críticas",
      "No hay elementos que requieran atención inmediata.",
      "Ejecutivo",
      "—",
      "",
    );

  const horizon30 = (() => {
    const d = new Date(hoyIso + "T12:00:00");
    d.setDate(d.getDate() + 30);
    return d.toISOString().slice(0, 10);
  })();
  const upcomingCombined = [];
  orderedPlan.forEach((x) => {
    if (
      x.finPlan &&
      x.finPlan >= hoyIso &&
      x.finPlan <= horizon30 &&
      !isClosed(x)
    )
      upcomingCombined.push({
        tipo:
          String(x.tipo || "").toLowerCase() === "hito" ? "hito" : "compromiso",
        titulo: x.actividad,
        responsable: x.responsable,
        fecha: x.finPlan,
        tag: isReview(x) ? "Por validar" : "",
      });
  });
  (ac.abiertas || []).forEach((x) => {
    if (x.fechaLimite && x.fechaLimite >= hoyIso && x.fechaLimite <= horizon30)
      upcomingCombined.push({
        tipo: "accion",
        titulo: x.accion,
        responsable: x.responsable,
        fecha: x.fechaLimite,
        tag: /cliente/i.test(String(x.dependencia || ""))
          ? "Decisión requerida"
          : "",
      });
  });
  upcomingCombined.sort(
    (a, b) =>
      String(a.fecha || "").localeCompare(String(b.fecha || "")) ||
      String(a.titulo || "").localeCompare(String(b.titulo || "")),
  );

  return {
    d,
    p,
    k,
    dims,
    total,
    cerrados,
    pctCerrados,
    pctATiempo,
    vencidos,
    vencenHoy,
    criticos,
    abiertosRiesgo,
    nextMilestone,
    nextMilestoneDate,
    nextMilestoneCount,
    durationPct,
    tiempoVsPlan,
    presupuestoPct,
    costoReal,
    depUnique,
    depVencidas,
    depAbiertas,
    depDetenidas,
    bloqueos,
    healthScore,
    badgeText,
    attn,
    upcomingCombined,
  };
}
