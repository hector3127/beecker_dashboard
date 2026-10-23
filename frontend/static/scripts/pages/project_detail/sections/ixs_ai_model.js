// Preserve the previous IA calculations; dependencies are explicit, with no DOM or network.

export function context(state, project, milestones) {
  const st = state,
    d = project || {},
    az = st.azure || {},
    p = st.plan || {},
    re = st.resources || {},
    clock = st.clockify || {};
  const wi = Array.isArray(az.allItems) ? az.allItems : [],
    resources = Array.isArray(re.filas) ? re.filas : [],
    registros = Array.isArray(clock.registros) ? clock.registros : [];
  const person = (w) => {
    const v = w.assignedTo || w.asignado || "";
    return typeof v === "object"
      ? v.displayName || v.name || v.uniqueName || ""
      : String(v);
  };
  const grouped = (rows, key) =>
    rows.reduce((out, x) => {
      const k = String(key(x) || "Sin asignar");
      out[k] = (out[k] || 0) + 1;
      return out;
    }, {});
  const totalHours = new Map(),
    dailyHours = new Map();
  registros.forEach((r) => {
    const name = String(r.recurso || r.nombre || r.usuario || "").trim(),
      hours = Number(r.duracion),
      day = String(r.fecha || "").slice(0, 10);
    if (!Number.isFinite(hours) || hours < 0) return;
    if (name) totalHours.set(name, (totalHours.get(name) || 0) + hours);
    if (day) dailyHours.set(day, (dailyHours.get(day) || 0) + hours);
  });
  const phases = milestones.map((h, i) => ({
    id: "ETAPA-" + (i + 1),
    nombre: h.name,
    inicio: h.start,
    fin: h.finish,
    estado: h.state,
    grupo: h.group || "",
    observacion: h.notes || "",
  }));
  const actions =
    (st.cliente && st.cliente.acciones && st.cliente.acciones.filas) || [];
  return {
    proyecto: st.id,
    nombreProyecto: (d.proyecto && d.proyecto.nombre) || "",
    fechaCorte: (d.proyecto && d.proyecto.fechaCorte) || "",
    etapaActual: (d.proyecto && d.proyecto.etapa) || "",
    avance: d.avance || {},
    presupuesto: d.presupuesto || {},
    kpis: d.kpisExtra || {},
    totalesRecursos: d.totalesRecursos || {},
    etapas: phases,
    fuentesDisponibles: [
      "dashboard",
      ...["azure", "plan", "resources", "clockify", "cliente", "raid"].filter(
        (k) => !!st[k],
      ),
    ],
    fuentesNoDisponibles: st.sourceErrors,
    workItems: wi.map((w) => ({
      id: w.id,
      titulo: w.title || w.titulo || "",
      estado: w.state || w.estado || "",
      asignado: person(w),
      iteracion: w.iterationPath || w.iteracion || "",
      fechaLimite: w.fechaLimiteDev || w.dueDate || "",
      tipo: w.tipo || "",
    })),
    workItemsTotal: wi.length,
    workItemsSinSeguimiento: (az.stale || []).length,
    workItemsPorEstado: grouped(wi, (w) => w.state || w.estado),
    workItemsPorIteracion: grouped(wi, (w) => w.iterationPath || w.iteracion),
    workItemsPorAsignado: grouped(wi, person),
    vacaciones: p.vacaciones || [],
    compromisos: p.compromisos || [],
    recursos: resources,
    horasPorRecurso: [...totalHours].map(([nombre, horas]) => ({
      nombre,
      horas: Number(horas.toFixed(2)),
    })),
    horasPorFecha: [...dailyHours].map(([fecha, horas]) => ({
      fecha,
      horas: Number(horas.toFixed(2)),
    })),
    horasClockifyTotal: Number(
      [...totalHours.values()].reduce((a, b) => a + b, 0).toFixed(2),
    ),
    registrosClockifyTotal: registros.length,
    acciones: actions,
    raid: (st.raid && st.raid.registros) || [],
    minutas: (st.minutas || [])
      .slice(0, 3)
      .map((m) => ({
        fecha: m.fecha,
        tema: m.tema,
        contenido: m.contenido.slice(0, 1200),
      })),
    memoriaAnterior:
      st.memoria && st.memoria.actual
        ? {
            fecha: st.memoria.actual.fecha,
            analisis: st.memoria.actual.analisis,
          }
        : null,
  };
}

export function snapshot(state, context) {
  const s = state,
    wi = (s.azure && s.azure.allItems) || [],
    clock = (s.clockify && s.clockify.registros) || [],
    resources = (s.resources && s.resources.filas) || [];
  const hours = clock.reduce((a, r) => a + (Number(r.duracion) || 0), 0);
  const closed = wi.filter((w) =>
    /closed|done|resolved|complet|cerrad/i.test(
      String(w.state || w.estado || ""),
    ),
  );
  return {
    proyecto: s.id,
    fuentes: context.fuentesDisponibles,
    workItems: wi.map((w) => ({
      id: String(w.id),
      estado: String(w.state || w.estado || ""),
    })),
    totalWorkItems: wi.length,
    cerrados: closed.length,
    horas: Number(hours.toFixed(2)),
    raidIds: ((s.raid && s.raid.registros) || []).map((r) => String(r.id)),
    acciones: (
      (s.cliente && s.cliente.acciones && s.cliente.acciones.filas) ||
      []
    ).map((a) => ({ uid: String(a.uid), estado: String(a.estado || "") })),
    recursos: resources.map((r) => ({
      nombre: r.nombre,
      estimadas: Number(r.horasEstimadas) || 0,
      activo: r.activo !== false,
    })),
    compromisos: (s.plan && s.plan.compromisos) || [],
    vacaciones: (s.plan && s.plan.vacaciones) || [],
  };
}

export function changes(state, snapshot) {
  const s = state,
    previous = s.memoria && s.memoria.actual && s.memoria.actual.snapshot;
  if (!previous) return null;
  const now = snapshot();
  if (
    !now.fuentes.includes("azure") ||
    !now.fuentes.includes("clockify") ||
    !previous.fuentes ||
    !previous.fuentes.includes("azure") ||
    !previous.fuentes.includes("clockify")
  )
    return { incompleto: true };
  const oldStates = new Map(
    (previous.workItems || []).map((x) => [
      String(x.id),
      String(x.estado || ""),
    ]),
  );
  const newClosed = now.workItems.filter(
    (w) =>
      /closed|done|resolved|complet|cerrad/i.test(w.estado) &&
      oldStates.has(w.id) &&
      !/closed|done|resolved|complet|cerrad/i.test(oldStates.get(w.id)),
  ).length;
  const added = now.workItems.filter((w) => !oldStates.has(w.id)).length;
  return {
    horas: Number((now.horas - (Number(previous.horas) || 0)).toFixed(2)),
    cerrados: newClosed,
    nuevos: added,
    nuevosRaid: now.raidIds.filter(
      (id) => !(previous.raidIds || []).includes(id),
    ).length,
    accionesCompletadas: now.acciones.filter(
      (a) =>
        /complet|cerrad/i.test(a.estado) &&
        (previous.acciones || []).some(
          (b) => b.uid === a.uid && !/complet|cerrad/i.test(b.estado),
        ),
    ).length,
    fecha: s.memoria.actual.fecha,
  };
}

export function capacity(state) {
  const s = state;
  if (!s.resources || !s.clockify) return [];
  const map = new Map(),
    key = (n) =>
      String(n || "")
        .trim()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/\s+/g, " ")
        .toLowerCase();
  (s.clockify.registros || []).forEach((r) => {
    const k = key(r.recurso);
    if (k) map.set(k, (map.get(k) || 0) + (Number(r.duracion) || 0));
  });
  return (s.resources.filas || [])
    .filter((r) => r.activo !== false)
    .map((r) => ({
      nombre: r.nombre,
      estimadas: Number(r.horasEstimadas) || 0,
      consumidas: Number((map.get(key(r.nombre)) || 0).toFixed(2)),
    }));
}
