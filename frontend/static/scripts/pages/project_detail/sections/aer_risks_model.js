import { normalize } from "./actions_model.js";

function mergeByCompleteness(prev, cur, fields) {
  const score = (o) =>
    (fields || []).reduce(
      (s, k) => s + (String((o || {})[k] || "").trim() ? 1 : 0),
      0,
    );
  const ps = score(prev),
    cs = score(cur);
  if (cs > ps) return Object.assign({}, prev || {}, cur || {});
  if (ps > cs) return Object.assign({}, cur || {}, prev || {});
  return Object.assign({}, prev || {}, cur || {});
}

export function dedupRisks(rows) {
  const exact = new Map();
  (rows || []).forEach((r) => {
    const key = [
      normalize(r.riesgo),
      normalize(r.responsable),
      String(r.fechaLimite || ""),
    ].join("|");
    if (!key.replace(/\|/g, "").trim()) return;
    const prev = exact.get(key);
    exact.set(
      key,
      prev
        ? mergeByCompleteness(prev, r, [
            "riesgo",
            "impacto",
            "probabilidad",
            "responsable",
            "fechaLimite",
            "accion",
            "estado",
            "notas",
          ])
        : r,
    );
  });
  const loose = new Map();
  [...exact.values()].forEach((r) => {
    const key = normalize(r.riesgo);
    if (!key) return;
    const prev = loose.get(key);
    if (!prev) {
      loose.set(key, r);
      return;
    }
    const sameResp =
      !normalize(prev.responsable) ||
      !normalize(r.responsable) ||
      normalize(prev.responsable) === normalize(r.responsable);
    const sameDate =
      !String(prev.fechaLimite || "") ||
      !String(r.fechaLimite || "") ||
      String(prev.fechaLimite || "") === String(r.fechaLimite || "");
    loose.set(
      key,
      sameResp && sameDate
        ? mergeByCompleteness(prev, r, [
            "riesgo",
            "impacto",
            "probabilidad",
            "responsable",
            "fechaLimite",
            "accion",
            "estado",
            "notas",
          ])
        : prev,
    );
  });
  return [...loose.values()];
}

export function risksModel(dashboard, now = new Date()) {
  const r = dashboard.riesgos || {},
    k = dashboard.kpis || {},
    ac = dashboard.acciones || {};
  const activos = dedupRisks(r.activos || []);
  const crit = activos.filter(
    (x) =>
      /alto|crit/i.test(String(x.impacto || "")) ||
      /alta|crit/i.test(String(x.probabilidad || "")),
  );
  const abiertos = activos.filter(
    (x) => !/cerr|mitigad|resuelto/i.test(String(x.estado || "")),
  );
  const matrix = {};
  activos.forEach((x) => {
    const key = `${String(x.probabilidad || "Media").toLowerCase()}|${String(x.impacto || "Medio").toLowerCase()}`;
    matrix[key] = (matrix[key] || 0) + 1;
  });
  const hoyIso = now.toISOString().slice(0, 10);
  const vencidasAcc = (ac.vencidas || []).filter(
    (x) => x.fechaLimite && x.fechaLimite < hoyIso,
  );
  const exposure =
    crit.length > 0
      ? "Alta"
      : activos.length >= 3
        ? "Media"
        : activos.length
          ? "Media"
          : "Baja";
  const abiertosCnt = abiertos.filter(
    (x) => /abiert|proposed/i.test(String(x.estado || "")) || !x.estado,
  ).length;
  const mitigCnt = abiertos.filter((x) =>
    /mitig|progreso/i.test(String(x.estado || "")),
  ).length;
  const cerrCnt = Math.max(0, activos.length - abiertosCnt - mitigCnt);
  const atencion = vencidasAcc[0] || (ac.vencidas || [])[0] || null;
  const riesgoPct = (x) =>
    Math.max(
      15,
      Math.min(
        95,
        100 -
          ((/alto|alta|crit/i.test(String(x.impacto || "")) ? 35 : 18) +
            (/alta|alto/i.test(String(x.probabilidad || "")) ? 25 : 10)),
      ),
    );

  return {
    r,
    k,
    ac,
    activos,
    crit,
    abiertos,
    matrix,
    hoyIso,
    vencidasAcc,
    exposure,
    abiertosCnt,
    mitigCnt,
    cerrCnt,
    atencion,
    riesgoPct,
    alerts: (dashboard.alertas || []).filter((x) => x.nivel !== "ok").length,
  };
}
