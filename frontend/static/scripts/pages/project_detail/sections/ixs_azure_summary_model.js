import { statusClass } from "./ixs_planning_azure.js";
import { groupStatus } from "./ixs_azure_groups_model.js";

export const statusColors = {
  Closed: "#6cd18b",
  Active: "#ad8cff",
  Proposed: "#7eb6ff",
  Blocked: "#ff819b",
  Other: "#ddd7fb",
};

function requirement(title) {
  const text = String(title || "").trim();
  return (
    (text.match(/[A-Z]{2,}\.[0-9]{3}(?:\.[0-9]{3})+/i) ||
      text.match(/[A-Z]{2,}\.[0-9]{3}(?:_[A-Z0-9]+)?/i) ||
      [])[0] || "—"
  );
}
function titleOnly(title) {
  const text = String(title || "").trim(),
    req = requirement(text);
  return req === "—"
    ? text
    : text
        .replace(req, "")
        .replace(/^[-–—:|\s]+/, "")
        .trim() || text;
}
function dateMs(value) {
  if (!value) return NaN;
  const lat = String(value).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (lat) return new Date(+lat[3], +lat[2] - 1, +lat[1], 12).getTime();
  const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m
    ? new Date(+m[1], +m[2] - 1, +m[3], 12).getTime()
    : new Date(value).getTime();
}

export function azureSummary(state) {
  const items = state.items || [],
    all = state.allItems || items,
    stale = state.stale || [];
  const total = all.length,
    closed = all.filter((x) => statusClass(x.estado) === "closed").length;
  const qa = items.filter((x) => !!x.qaListo).length;
  const avg = items.length
    ? Math.round(
        items.reduce((a, b) => a + (Number(b.avanceTotal) || 0), 0) /
          items.length,
      )
    : 0;
  const riskIds = new Set();
  stale.forEach((x) => {
    if (
      /risk|issue|block/i.test(String(x.tipo || "")) ||
      statusClass(x.estado) === "blocked"
    )
      riskIds.add(String(x.id || x.titulo || Math.random()));
  });
  all.forEach((x) => {
    if (statusClass(x.estado) === "blocked")
      riskIds.add(String(x.id || x.titulo || Math.random()));
  });
  const riskCount = riskIds.size;
  const counts = { Closed: 0, Active: 0, Proposed: 0, Blocked: 0, Other: 0 };
  all.forEach((x) => {
    const cls = statusClass(x.estado);
    counts[
      {
        closed: "Closed",
        active: "Active",
        proposed: "Proposed",
        blocked: "Blocked",
      }[cls] || "Other"
    ]++;
  });
  const entries = Object.entries(counts).filter((x) => x[1] > 0),
    totalDist = entries.reduce((a, b) => a + b[1], 0) || 1;
  let acc = 0;
  const stops = entries.map(([name, value]) => {
    const start = (acc * 100) / totalDist;
    acc += value;
    return `${statusColors[name]} ${start}% ${(acc * 100) / totalDist}%`;
  });
  const donut =
    "conic-gradient(" +
    (stops.length ? stops.join(", ") : "#ece9fa 0 100%") +
    ")";
  const notes = [
    {
      cls: stale.length ? "bad" : "",
      text: stale.length
        ? `${stale.length} ítems sin seguimiento por más de 7 días.`
        : "No hay ítems sin seguimiento por más de 7 días.",
    },
    {
      cls: total && closed > total / 2 ? "" : "warn",
      text:
        total && closed > total / 2
          ? "La mayoría de los Work Items ya está cerrada."
          : "Hay Work Items que siguen abiertos.",
    },
  ];
  if (riskCount)
    notes.push({
      cls: "warn",
      text: `${riskCount} ítems con riesgo o bloqueo registrado.`,
    });
  notes.push({
    cls: avg >= 80 ? "" : "warn",
    text: `Avance promedio de ${avg}% en los Work Items con seguimiento de avance.`,
  });
  const byAssigned = Object.values(
    all.reduce((result, item) => {
      const nombre =
        String(item.asignadoA || "Sin asignar").trim() || "Sin asignar";
      if (!result[nombre])
        result[nombre] = { nombre, total: 0, abiertos: 0, cerrados: 0 };
      result[nombre].total++;
      const status = groupStatus(item.estado);
      if (status === "closed" || status === "cancelled")
        result[nombre].cerrados++;
      else result[nombre].abiertos++;
      return result;
    }, {}),
  ).sort(
    (a, b) =>
      b.abiertos - a.abiertos ||
      b.total - a.total ||
      a.nombre.localeCompare(b.nombre, "es"),
  );
  const maxOpen = Math.max(1, ...byAssigned.map((x) => x.abiertos));
  const byDate = items
    .filter((x) => x.fechaLimiteDev)
    .map((x) => ({
      fecha: x.fechaLimiteDev,
      req: requirement(x.titulo),
      titulo: titleOnly(x.titulo),
      url: x.url || "#",
    }))
    .sort((a, b) => dateMs(a.fecha) - dateMs(b.fecha))
    .slice(0, 8);
  const staleSorted = [...stale]
    .sort(
      (a, b) =>
        (Number(b.diasSinActualizar) || 0) - (Number(a.diasSinActualizar) || 0),
    )
    .slice(0, 8);
  return {
    total,
    closed,
    qa,
    avg,
    riskCount,
    entries,
    totalDist,
    donut,
    notes,
    byAssigned,
    maxOpen,
    byDate,
    staleSorted,
    staleCount: stale.length,
  };
}
