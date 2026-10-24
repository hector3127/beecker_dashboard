export function weekRange(now = new Date()) {
  const d = new Date(now);
  d.setHours(12, 0, 0, 0);
  const day = d.getDay(),
    diff = day === 0 ? -6 : 1 - day;
  const ini = new Date(d);
  ini.setDate(d.getDate() + diff);
  const fin = new Date(ini);
  fin.setDate(ini.getDate() + 6);
  return {
    desde: ini.toISOString().slice(0, 10),
    hasta: fin.toISOString().slice(0, 10),
  };
}
export function initialState(state, now = new Date()) {
  return state.desde && state.hasta
    ? { ...state }
    : { ...state, ...weekRange(now) };
}
export function currentRecords(dashboard, state) {
  const base = Array.isArray(state.registros)
    ? state.registros
    : dashboard.registros || [];
  return base.filter(
    (x) => x.fecha && x.fecha >= state.desde && x.fecha <= state.hasta,
  );
}
export function effortModel(dashboard, state, now = new Date()) {
  state = initialState(state, now);
  const d = dashboard,
    k = d.kpis || {},
    tasks = (d.tareas || []).slice(0, 8),
    recursos = (d.detalleRecursos || []).slice(0, 10),
    trend = d.tendenciaMensual || [];
  const regs = currentRecords(dashboard, state),
    previewCount = 5,
    regsPreview = regs.slice(0, previewCount);
  const maxTask = Math.max(1, ...tasks.map((x) => Number(x.horas || 0))),
    maxMes = Math.max(1, ...trend.map((x) => Number(x.horas || 0)));
  const fact = Number(k.pctFacturables || 0),
    noFact = Number(k.pctNoFacturables || 0),
    outPct = Number(k.pctFueraHorario || 0),
    totalPct = Number(k.consumoPct || 0);
  return {
    k,
    tasks,
    recursos,
    trend,
    regs,
    previewCount,
    regsPreview,
    maxTask,
    maxMes,
    fact,
    noFact,
    outPct,
    totalPct,
    state,
  };
}
