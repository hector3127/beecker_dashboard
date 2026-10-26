export const palette = [
  "#4A2A94",
  "#E0298B",
  "#8B5CF6",
  "#F472B6",
  "#6D28D9",
  "#C026A3",
];
export function barsModel(items) {
  const max = Math.max(
    1,
    ...items.map((row) => Math.max(row.horasEstimadas, row.horasReales)),
  );
  return items.map((row) => ({
    name: String(row.nombre),
    hours: `${row.horasReales} / ${row.horasEstimadas} hrs`,
    estimated: (row.horasEstimadas / max) * 100,
    real: (row.horasReales / max) * 100,
  }));
}
export function chartsModel(data) {
  const total =
    Math.round(
      data.distribucionArea.reduce((sum, row) => sum + row.horas, 0) * 10,
    ) / 10;
  const circle = 2 * Math.PI * 77;
  let accumulated = 0;
  const areas = data.distribucionArea.map((row, index) => {
    const fraction = total ? row.horas / total : 0;
    const arc = fraction * circle,
      offset = -accumulated * circle;
    accumulated += fraction;
    return {
      name: String(row.nombre),
      hours: row.horas + "h",
      pct: row.pct + "%",
      color: palette[index % palette.length],
      dash: `${arc} ${circle - arc}`,
      offset,
    };
  });
  return {
    areas,
    total: Math.round((total + Number.EPSILON) * 10) / 10,
    resources: barsModel(
      (data.filasRecursosCompleto || [])
        .slice()
        .sort((a, b) => b.horasReales - a.horasReales)
        .map((row) => ({
          nombre: row.nombre + (row.posicion ? " — " + row.posicion : ""),
          horasEstimadas: row.horasEstimadas,
          horasReales: row.horasReales,
        })),
    ),
    roles: barsModel(
      (data.porRol || []).map((row) => ({
        nombre: row.rol,
        horasEstimadas: row.horasEstimadas,
        horasReales: row.horasReales,
      })),
    ),
  };
}
