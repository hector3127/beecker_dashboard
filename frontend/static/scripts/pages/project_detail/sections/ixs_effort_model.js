import { resourceKey } from "./ixs_executive_model.js";

export function effortModel(d) {
  const rows = (d && d.filasRecursosCompleto) || [],
    tot = (d && d.totalesRecursos) || {},
    ke = (d && d.kpisExtra) || {};
  const round = (x) => Math.round(Number(x || 0) * 100) / 100;
  const billable = Number(
    tot.horasReales ||
      rows.reduce((a, x) => a + Number(x.horasReales || 0), 0) ||
      0,
  );
  const estimadas = Number(
    tot.horasEstimadas ||
      rows.reduce((a, x) => a + Number(x.horasEstimadas || 0), 0) ||
      0,
  );
  const noFact = Number(
    tot.horasNoFact ||
      rows.reduce((a, x) => a + Number(x.horasNoFact || 0), 0) ||
      0,
  );
  const fact = billable,
    real = round(billable + noFact);
  const fueraHorario = Number(ke.horasFueraHorario || d.horasFueraHorario || 0);
  const balance = round(estimadas - real);
  return {
    real: real,
    estimadas: estimadas,
    noFact: noFact,
    fact: fact,
    fueraHorario: fueraHorario,
    pctFact: real ? (fact * 100) / real : 0,
    pctNoFact: real ? (noFact * 100) / real : 0,
    pctFuera: real ? (fueraHorario * 100) / real : 0,
    pctConsumo: estimadas ? (real * 100) / estimadas : 0,
    balance: balance,
    costoReal: Number(tot.costoReal || 0),
    costoPct: Number(
      tot.pctCumplimientoFinanciero || ke.pctCumplimientoFinanciero || 0,
    ),
  };
}

export function excessByPerson(resources, records) {
  const people = new Map();
  (resources || []).forEach((x) =>
    people.set(resourceKey(x.nombre), {
      name: x.nombre,
      role: x.posicion || "Sin rol",
      budget: Math.max(0, Number(x.horasEstimadas) || 0),
      used: 0,
      excess: 0,
      records: [],
    }),
  );
  const seen = new Set();
  const ordered = (records || [])
    .map((x, i) => ({ ...x, _order: i }))
    .sort(
      (a, b) =>
        (String(a.fecha || "") + " " + String(a.inicio || "")).localeCompare(
          String(b.fecha || "") + " " + String(b.inicio || ""),
        ) || a._order - b._order,
    );
  ordered.forEach((x) => {
    if (x.billable !== true) return;
    if (x.id) {
      if (seen.has(x.id)) return;
      seen.add(x.id);
    }
    const key = resourceKey(x.recurso),
      hours = Number(x.duracion);
    if (!key || !Number.isFinite(hours) || hours <= 0) return;
    if (!people.has(key))
      people.set(key, {
        name: x.recurso,
        role: "Sin asignación",
        budget: 0,
        used: 0,
        excess: 0,
        records: [],
      });
    const person = people.get(key),
      before = person.used;
    person.used += hours;
    const excess =
      Math.max(0, person.used - person.budget) -
      Math.max(0, before - person.budget);
    if (excess > 0.000001) {
      person.excess += excess;
      person.records.push({ ...x, excess: excess, cumulative: person.used });
    }
  });
  return [...people.values()]
    .filter((x) => x.records.length)
    .sort((a, b) => b.excess - a.excess);
}

export function activityRows(regs) {
  // Agrupación de los registros ya consultados del proyecto, sin peticiones nuevas a Clockify.
  // Las sumas utilizan los registros reales, no el corte de la semana del cuadro inferior.
  const tasks = new Map();
  (regs || []).forEach((x) => {
    const nombre = String(x.actividad || "Sin task").trim() || "Sin task";
    const persona = String(x.recurso || "Sin recurso").trim() || "Sin recurso";
    const horas = Number(x.duracion || 0);
    if (!tasks.has(nombre))
      tasks.set(nombre, {
        nombre,
        horas: 0,
        registros: 0,
        personas: new Map(),
      });
    const task = tasks.get(nombre);
    task.horas += horas;
    task.registros++;
    if (!task.personas.has(persona))
      task.personas.set(persona, { nombre: persona, horas: 0, registros: [] });
    const recurso = task.personas.get(persona);
    recurso.horas += horas;
    recurso.registros.push(x);
  });
  return Array.from(tasks.values())
    .map((task) => ({
      nombre: task.nombre,
      horas: task.horas,
      registros: task.registros,
      personas: Array.from(task.personas.values()).sort(
        (a, b) => b.horas - a.horas || a.nombre.localeCompare(b.nombre, "es"),
      ),
    }))
    .sort(
      (a, b) => b.horas - a.horas || a.nombre.localeCompare(b.nombre, "es"),
    );
}

export function trendRows(regs) {
  const m = new Map();
  (regs || []).forEach((x) => {
    const key = String(x.fecha || "").slice(0, 7);
    if (!/^\d{4}-\d{2}$/.test(key)) return;
    m.set(key, (m.get(key) || 0) + Number(x.duracion || 0));
  });
  return Array.from(m, ([mes, horas]) => ({ mes, horas }))
    .sort((a, b) => a.mes.localeCompare(b.mes))
    .slice(-5);
}

export function ymdLocal(v) {
  const d = v instanceof Date ? v : new Date(v);
  if (isNaN(d.getTime())) return "";
  return (
    d.getFullYear() +
    "-" +
    String(d.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(d.getDate()).padStart(2, "0")
  );
}

export function currentWeek() {
  const today = new Date(),
    from = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  from.setDate(from.getDate() - ((from.getDay() + 6) % 7));
  const to = new Date(from);
  to.setDate(to.getDate() + 6);
  return { desde: ymdLocal(from), hasta: ymdLocal(to) };
}
