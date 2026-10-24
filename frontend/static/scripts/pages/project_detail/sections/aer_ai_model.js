export function today(now = new Date()) {
  const d = new Date(now);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}
export function context(dashboard, state, now = new Date()) {
  const d = dashboard || {},
    k = d.kpis || {};
  const list = (obj) => (obj || {}).filas || [];
  const plan = list(d.plan),
    rec = d.detalleRecursos || [];
  const occupied = plan
    .filter((x) => !/completado|detenido|por validar/i.test(x.estado || ""))
    .reduce((map, x) => {
      const r = String(x.responsable || "").trim();
      if (r && r.toLowerCase() !== "pendiente")
        map[r] = (map[r] || 0) + Number(x.esfuerzo || 0);
      return map;
    }, {});
  return {
    id: (d.proyecto || {}).id || "",
    n: (d.proyecto || {}).nombre || "",
    cliente: (d.proyecto || {}).cliente || "",
    etapa: (d.proyecto || {}).etapa || "",
    fecha: today(now),
    k: {
      horas: Number(k.horasTotales || 0),
      fact: Number(k.horasFacturables || 0),
      presupuesto: Number(k.budgetHoras || 0),
      consumoPct: Number(k.consumoPct || 0),
      tiempoPct: Number(k.pctTiempo || 0),
      health: Number(k.healthScore || 0),
      vencidos: Number((d.plan || {}).vencidosAbiertos || 0),
      desviacion: Number(k.desviacionPts || 0),
      horasFueraHorario: Number(k.horasFueraHorario || 0),
    },
    p: plan.slice(0, 28).map((x) => ({
      a: x.actividad,
      r: x.responsable,
      f: x.finPlan,
      e: x.estado,
      z: x.esfuerzo,
      d: x.dependencia,
    })),
    r: list(d.riesgos).map((x) => ({ a: x.riesgo, i: x.impacto, e: x.estado })),
    a: list(d.acciones).map((x) => ({
      a: x.accion,
      r: x.responsable,
      f: x.fechaLimite,
      e: x.estado,
    })),
    v: list(d.vacaciones)
      .filter((x) => /aprobada/i.test(x.estado || ""))
      .map((x) => ({ r: x.recurso, i: x.inicio, f: x.fin, e: x.estado })),
    c: Object.keys(occupied).map((x) => ({ r: x, o: occupied[x] })),
    b: (state.accionesPartes || [])
      .filter((x) => x.estado !== "Completado")
      .map((x) => ({
        a: x.accion,
        o: x.responsable,
        f: x.fechaLimite,
        e: x.estado,
        n: x.notas,
      })),
  };
}
export function facts(dashboard, state, now = new Date()) {
  const c = context(dashboard, state, now),
    h = c.fecha,
    lim = new Date(h + "T12:00:00");
  lim.setDate(lim.getDate() + 30);
  const to = lim.toISOString().slice(0, 10);
  const activos = c.p.filter(
    (x) => !/completado|detenido|por validar/i.test(x.e || ""),
  );
  const venc = activos.filter((x) => x.f && x.f < h),
    prox = activos.filter((x) => x.f && x.f >= h && x.f <= to);
  const sobre = c.c.filter((x) => x.o > 6),
    vac = c.v.filter((x) => x.i && x.f && x.f >= h && x.i <= to);
  const abiertos = c.a.filter((x) => !/completado|cerrado/i.test(x.e || ""));
  const riesgo = c.r.filter((x) => !/completado|cerrado/i.test(x.e || ""));
  const alerts = [];
  if (venc.length) alerts.push(venc.length + " compromiso(s) vencido(s)");
  if (sobre.length)
    alerts.push(sobre.length + " recurso(s) con esfuerzo superior a 6 puntos");
  if (vac.length)
    alerts.push(vac.length + " vacaciones aprobadas en los próximos 30 días");
  if (c.k.horas > c.k.presupuesto && c.k.presupuesto)
    alerts.push("Horas consumidas superan el presupuesto");
  return { c, activos, venc, prox, sobre, vac, abiertos, riesgo, alerts, to };
}
