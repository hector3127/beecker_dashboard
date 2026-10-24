// Unchanged derivations from the shared AER/IXS Actions tab.
export const STATES = ["Pendiente", "En progreso", "Detenido", "Completado"];
export const PRIORITIES = ["Alta", "Media", "Baja"];
export function normalize(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
}
export function dateText(value) {
  if (!value) return "—";
  const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : String(value);
}
export function stateClass(value) {
  const s = normalize(value);
  if (/vencid|crit|alto|alerta/.test(s)) return "bad";
  if (/complet|cerrad|ok|salud/.test(s)) return "ok";
  if (/detenid|paus|bloq|mitig/.test(s)) return "warn";
  if (/por validar|revision/.test(s)) return "review";
  if (/en progreso|abiert|seguimiento|curso/.test(s)) return "info";
  return "soft";
}
export function progress(value) {
  const s = String(value || "").toLowerCase();
  return s.includes("complet")
    ? 100
    : s.includes("progreso")
      ? 65
      : s.includes("detenido")
        ? 35
        : 10;
}
export function dependencies(value) {
  const options = ["", "Cliente", "Interna", "NA"],
    current = String(value || "");
  if (current && !options.includes(current)) options.splice(1, 0, current);
  return options;
}
export function actionDate(x) {
  return (
    x.fechaLimite || x.proximaRevision || x.fechaReal || x.fechaInicio || ""
  );
}
export function actionsModel(
  dashboard,
  today = new Date().toISOString().slice(0, 10),
) {
  const ac = dashboard.acciones || {},
    filas = ac.filas || [];
  const hoyIso = today;
  const abiertas = (ac.abiertas || []).length,
    vencidas = (ac.vencidas || []).length,
    detenidas = (ac.detenidas || []).length;
  const proximas =
    filas
      .filter((x) => actionDate(x))
      .sort((a, b) =>
        String(actionDate(a)).localeCompare(String(actionDate(b))),
      )[0] || null;
  const urgente =
    (ac.vencidas || [])[0] ||
    filas.find((x) =>
      String(x.estado || "")
        .toLowerCase()
        .includes("detenido"),
    ) ||
    filas[0] ||
    null;
  const respCount = {};
  (filas || []).forEach((x) => {
    const r = String(x.responsable || "").trim() || "Sin responsable";
    respCount[r] = (respCount[r] || 0) + 1;
  });
  const respTop = Object.entries(respCount).sort(
    (a, b) => b[1] - a[1] || a[0].localeCompare(b[0]),
  )[0];
  const weeks = [];
  let d0 = new Date(hoyIso + "T12:00:00");
  for (let i = 0; i < 5; i++) {
    const d = new Date(d0.getTime() + i * 7 * 86400000);
    const iso = d.toISOString().slice(0, 10);
    const cnt = filas.filter((x) => {
      const f = actionDate(x);
      if (!f) return false;
      const diff = (new Date(f + "T12:00:00") - d) / 86400000;
      return diff >= 0 && diff < 7;
    }).length;
    weeks.push({ iso, cnt });
  }
  return {
    ac,
    filas,
    hoyIso,
    abiertas,
    vencidas,
    detenidas,
    proximas,
    urgente,
    respCount,
    respTop,
    weeks,
  };
}
