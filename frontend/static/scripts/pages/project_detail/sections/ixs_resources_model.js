import { resourceKey } from "./ixs_executive_model.js";

/** Same merge, hours and warnings as _ixsPintarRecursos. */
export function resourcesModel(d, st) {
  const base = (d.filasRecursosCompleto || []).filter((x) => x.nombre),
    map = new Map();
  base.forEach((x) => {
    const key = resourceKey(x.nombre);
    if (key && !map.has(key))
      map.set(key, {
        nombre: x.nombre,
        rol: x.posicion || "",
        horasEstimadas: Number(x.horasEstimadas) || 0,
        activo: true,
      });
  });
  st.filas.forEach((x) => {
    const key = resourceKey(x.nombre);
    if (key) map.set(key, Object.assign({}, map.get(key) || {}, x));
  });
  const hours = new Map();
  st.registros.forEach((r) => {
    const key = resourceKey(r.recurso),
      n = Number(r.duracion);
    if (!key || !Number.isFinite(n)) return;
    const prev = hours.get(key) || { nombre: r.recurso, horas: 0 };
    prev.horas += n;
    hours.set(key, prev);
  });
  const rows = [...map].sort((a, b) =>
    a[1].nombre.localeCompare(b[1].nombre, "es"),
  );
  const missing = [...hours].filter(([key, x]) => x.horas > 0 && !map.has(key));
  const inactive = rows.filter(
    ([key, x]) => !x.activo && (hours.get(key) || {}).horas > 0,
  );
  return { rows, hours, missing, inactive };
}

export function resourceEditorSource(data, state, name) {
  return (
    (state.filas || []).find(
      (x) => resourceKey(x.nombre) === resourceKey(name),
    ) ||
    (data.filasRecursosCompleto || []).find(
      (x) => resourceKey(x.nombre) === resourceKey(name),
    ) ||
    {}
  );
}
