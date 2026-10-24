import { resources } from "./aer_planning_model.js";

export function category(score) {
  score = Number(score) || 0;
  return score >= 90
    ? "Alto desempeño"
    : score >= 80
      ? "Sólido"
      : score >= 70
        ? "En seguimiento"
        : "Crítico";
}
export function categoryClass(score) {
  score = Number(score) || 0;
  return score >= 90
    ? "green"
    : score >= 80
      ? "purple"
      : score >= 70
        ? "yellow"
        : "red";
}
export function dateKey(v) {
  if (!v) return 0;
  const s = String(v).trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return Number(`${m[1]}${m[2]}${m[3]}`);
  m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (m) return Number(`${m[3]}${m[2]}${m[1]}`);
  const t = Date.parse(s);
  return Number.isFinite(t) ? t : 0;
}
export function resourcesModel(dashboard, selected = "") {
  const ev = (dashboard.evaluaciones?.filas || []).slice();
  const evOrdenadas = ev
    .slice()
    .sort((a, b) => dateKey(b.fechaEvaluacion) - dateKey(a.fechaEvaluacion));
  const recursos = resources(dashboard);
  if (!selected || !recursos.includes(selected)) selected = recursos[0] || "";
  const porRecurso = {};
  ev.forEach((x) => {
    if (!porRecurso[x.recurso]) porRecurso[x.recurso] = [];
    porRecurso[x.recurso].push(x);
  });
  Object.values(porRecurso).forEach((a) =>
    a.sort((x, y) => dateKey(x.fechaEvaluacion) - dateKey(y.fechaEvaluacion)),
  );
  const latest = Object.values(porRecurso)
    .map((a) => a[a.length - 1])
    .filter(Boolean);
  const avg = latest.length
    ? Math.round(
        latest.reduce((s, x) => s + Number(x.score || 0), 0) / latest.length,
      )
    : 0;
  const pendientes = Math.max(0, recursos.length - latest.length),
    observacion = latest.filter((x) => Number(x.score || 0) < 80).length,
    top = latest.filter((x) => Number(x.score || 0) >= 90).length;
  const hist = porRecurso[selected] || [],
    sel = hist[hist.length - 1] || {
      recurso: selected,
      score: 0,
      calidad: 0,
      cumplimiento: 0,
      comunicacion: 0,
      colaboracion: 0,
      autonomia: 0,
      categoria: "Sin evaluación",
    };
  const pts = evOrdenadas.slice(0, 5).reverse(),
    xs = pts.map((_, i) =>
      pts.length <= 1 ? 50 : 10 + i * (80 / (pts.length - 1)),
    ),
    ys = pts.map((x) => 90 - Number(x.score || 0) * 0.75),
    poly = pts.map((x, i) => `${xs[i]},${ys[i]}`).join(" ");
  const ptsDelta =
    pts.length > 1
      ? Number(pts[pts.length - 1].score || 0) - Number(pts[0].score || 0)
      : 0;
  const cats = {
    "Alto desempeño": 0,
    Sólido: 0,
    "En seguimiento": 0,
    Crítico: 0,
  };
  latest.forEach((x) => cats[category(x.score)]++);
  const totalCat = Math.max(1, latest.length),
    a1 = (cats["Alto desempeño"] / totalCat) * 100,
    a2 = a1 + (cats["Sólido"] / totalCat) * 100,
    a3 = a2 + (cats["En seguimiento"] / totalCat) * 100;
  const prox = ev
    .filter((x) => x.proximaEvaluacion)
    .sort(
      (a, b) => dateKey(a.proximaEvaluacion) - dateKey(b.proximaEvaluacion),
    )[0];
  const strengths = [
    ["Calidad", sel.calidad],
    ["Cumplimiento", sel.cumplimiento],
    ["Comunicación", sel.comunicacion],
    ["Colaboración", sel.colaboracion],
    ["Autonomía", sel.autonomia],
  ]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .filter((x) => x[1] > 0);
  return {
    ev,
    evOrdenadas,
    recursos,
    selected,
    porRecurso,
    latest,
    avg,
    pendientes,
    observacion,
    top,
    hist,
    sel,
    pts,
    xs,
    ys,
    poly,
    ptsDelta,
    cats,
    totalCat,
    a1,
    a2,
    a3,
    prox,
    strengths,
  };
}
