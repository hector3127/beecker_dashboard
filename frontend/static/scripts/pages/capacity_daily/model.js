// @ts-check
// Reglas de la pantalla anterior, aisladas del DOM y de las llamadas RPC.

/** @param {any} value */
export const norm = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
/** @param {any} row */
export const key = (row) => `${row.idProyecto}|${row.iteration}`;
/** @param {any} value */
export const fmt = (value) => Number(value || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 });
/** @param {string} value */
export const date = (value) => value ? `${value.slice(8, 10)}/${value.slice(5, 7)}/${value.slice(0, 4)}` : '—';

/** @param {string} month */
export function days(month) {
  const [year, number] = month.split('-').map(Number), out = [];
  for (const day = new Date(Date.UTC(year, number - 1, 1)); day.getUTCMonth() === number - 1; day.setUTCDate(day.getUTCDate() + 1)) {
    if (day.getUTCDay() !== 0 && day.getUTCDay() !== 6) out.push(day.toISOString().slice(0, 10));
  }
  return out;
}

/** @param {any} st */
export function computed(st) {
  const d = days(st.mes), all = [], people = new Map();
  (st.base && st.base.filas || []).filter((/** @type {any} */ f) => norm(f.concepto) !== 'sin asignacion').forEach((/** @type {any} */ f) => {
    const last = new Date(Date.UTC(Number(st.mes.slice(0, 4)), Number(st.mes.slice(5)), 0)).toISOString().slice(0, 10);
    const meta = f.idProyecto ? st.meta.get(key(f)) : { ok: true, inicio: st.mes + '-01', fin: last };
    if (f.idProyecto && meta && (meta.fueraMes || (meta.inicio && meta.fin && (meta.fin < st.mes + '-01' || meta.inicio > last)))) return;
    const status = !meta ? 'Consultando Clockify' : !meta.ok ? meta.error : !f.regla ? 'Concepto sin regla' : null;
    const values = d.map((day) => !f.idProyecto ? 0 : meta && meta.ok ? Number((meta.daily[norm(f.recurso)] || {})[day] || 0) : null);
    const total = values.reduce((n, value) => n + (value || 0), 0);
    all.push(Object.assign({}, f, { inicio: meta && meta.inicio, fin: meta && meta.fin, values, total, status, per: null }));
    const k = norm(f.recurso).trim();
    if (!people.has(k)) people.set(k, { nombre: f.recurso, tecnologia: f.tecnologia, banda: f.banda, values: d.map(() => 0), total: 0, fact: 0, carg: 0, unknown: false });
    const p = people.get(k);
    if (status) p.unknown = true;
    if (f.regla && f.regla.afecta) { values.forEach((value, i) => p.values[i] += value || 0); p.total += total; }
    if (f.regla && f.regla.facturable === 'Facturable') p.fact += total;
    if (f.regla && f.regla.cargabilidad === 'Cargable') p.carg += total;
  });
  const available = Array.from(people.values()).reduce((n, p) => n + p.values.reduce((/** @type {number} */ s, /** @type {number} */ v) => s + Math.max(0, st.jornada - v), 0), 0);
  return { days: d, all, people: Array.from(people.values()), available };
}

/** @param {any[]} rows @param {any} st */
export function selected(rows, st) {
  return rows.filter((x) => (!st.tecnologia || x.tecnologia === st.tecnologia) && (!st.concepto || x.concepto === st.concepto) && (!st.q || norm([x.recurso, x.idProyecto, x.proyecto, x.manager, x.rol, x.banda].join(' ')).includes(norm(st.q))));
}

/** @param {ReturnType<typeof computed>} data @param {any[]} rows */
export function csv(data, rows) {
  const head = ['RECURSO', 'Banda', 'Conceptos', 'Facturable', 'Cargabilidad', 'Capacidad Disponible', 'Tecnología', 'Delivery Manager', 'ID Proyecto', 'Proyecto', 'Inicio', 'Fin', 'Total mes', ...data.days.map(date)];
  const records = rows.map((f) => [f.recurso, f.banda, f.concepto, f.regla && f.regla.facturable, f.regla && f.regla.cargabilidad, f.regla && f.regla.capacidad, f.tecnologia, f.manager, f.idProyecto, f.proyecto, f.inicio, f.fin, f.total, ...f.values]);
  return '\ufeff' + [head, ...records].map((row) => row.map((v) => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"').join(',')).join('\r\n');
}
