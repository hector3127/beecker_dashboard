// Unchanged derivations from the shared AER/IXS Actions tab.
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
