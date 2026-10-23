export const months = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];
export const cats = [
  "Facturable",
  "No Facturables",
  "Administrativo Operaciones",
  "Inversión Operaciones",
  "Inversión Comercial",
  "Administrativas",
  "Continuos Improvement",
  "Vacaciones",
  "Laboratorio",
  "Pre-Venta",
  "Internos",
  "Sin Asignación",
  "Optimización",
  "Agentes Autónomos",
];

// Calculations extracted from the previous screen, without changing their rules.
export const num = (n) =>
  n == null
    ? "NA"
    : Number(n).toLocaleString("es-MX", { maximumFractionDigits: 2 });
export const norm = (s) =>
  String(s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
export const colors = [
  "#7944ef",
  "#477bfd",
  "#efa72a",
  "#28ba7b",
  "#ea62ad",
  "#785af0",
];
export function createModel(state, selection) {
  const key = (i) => state.year + "-" + String(i + 1).padStart(2, "0");
  function aggregate(i) {
    const r = state.data[key(i)];
    if (!r || !r.ok) return null;
    const aa = r.areas.filter((a) => !state.area || a.area === state.area),
      out = { horas: 0, recursos: 0, categorias: {} };
    aa.forEach((a) => {
      out.horas += a.horas;
      if (a.recursos == null) out.recursos = null;
      else if (out.recursos != null) out.recursos += a.recursos;
      cats.forEach((c) => {
        if (a.categorias[c] === null || out.categorias[c] === null)
          out.categorias[c] = null;
        else
          out.categorias[c] = (out.categorias[c] || 0) + (a.categorias[c] || 0);
      });
    });
    return out;
  }
  function workdays(i) {
    let n = 0;
    const end = new Date(state.year, i + 1, 0).getDate();
    for (let d = 1; d <= end; d++) {
      const w = new Date(state.year, i, d).getDay();
      if (w !== 0 && w !== 6) n++;
    }
    return Math.max(0, n - (state.holidays[i] || 0));
  }
  function gseKPICategories(d, norm) {
    const cs = Array.isArray(d.categorias) ? d.categorias.slice() : [],
      type = norm(d.tipo).replace(/[^a-z]/g, "");
    if (!cs.includes("Facturable") && !cs.includes("No Facturables")) {
      if (["facturable", "billable", "yes", "si"].includes(type))
        cs.push("Facturable");
      else if (
        [
          "nofacturable",
          "nofacturables",
          "nonbillable",
          "notbillable",
          "no",
        ].includes(type)
      )
        cs.push("No Facturables");
    }
    // Compatibilidad con detalles guardados antes de conservar categorias.
    const names = [
      "Administrativas",
      "Sin Asignación",
      "Optimización",
      "Inversión Operaciones",
      "Inversión Comercial",
      "Vacaciones",
      "Pre-Venta",
      "Laboratorio",
      "Internos",
      "Agentes Autónomos",
      "Continuos Improvement",
    ];
    for (const part of String(d.categoria || "").split(" / ")) {
      const match = names.find((c) => norm(c) === norm(part));
      if (match && !cs.includes(match)) cs.push(match);
    }
    if (
      !cs.includes("Facturable") &&
      !cs.includes("No Facturables") &&
      cs.some((c) =>
        [
          "Administrativas",
          "Sin Asignación",
          "Vacaciones",
          "Laboratorio",
          "Internos",
          "Continuos Improvement",
        ].includes(c),
      )
    )
      cs.push("No Facturables");
    return cs;
  }
  function gseKPIMetrics() {
    const kpiPerson = selection.kpiPerson,
      kpiMonth = selection.kpiMonth;
    const normalize = (s) =>
        String(s || "")
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase()
          .trim()
          .replace(/\s+/g, " "),
      services = ["AER", "TYM", "IxB", "SaaS", "RaaS", "Otros"],
      weights = { AER: 4, TYM: 2, IxB: 3, SaaS: 6, RaaS: 5, Otros: 1 };
    const employeeNames = new Map(),
      people = new Map();
    const valid = months.map(
      (_, i) =>
        state.data[key(i)]?.ok && Array.isArray(state.data[key(i)].detalle),
    );
    const monthly = months.map(() => ({
      total: 0,
      fact: 0,
      non: 0,
      carg: 0,
      nocarg: 0,
      affect: 0,
      noaffect: 0,
      weighted: 0,
      cap: 0,
      people: new Set(),
      svc: Object.fromEntries(services.map((s) => [s, 0])),
      invop: 0,
      invprod: 0,
      invcom: 0,
      unknown: 0,
    }));
    months.forEach((_, i) => {
      if (!valid[i]) return;
      const seen = new Set();
      for (const d of state.data[key(i)].detalle) {
        if (state.area && d.area !== state.area) continue;
        const name = normalize(d.recurso);
        employeeNames.set(name, d.recurso);
        if (kpiPerson && name !== kpiPerson) continue;
        const h = Number(d.horas) || 0;
        if (!(h > 0)) continue;
        if (d.id) {
          if (seen.has(d.id)) continue;
          seen.add(d.id);
        }
        const cs = gseKPICategories(d, normalize),
          m = monthly[i],
          cat = normalize(d.categoria),
          raw = normalize(d.servicio).replace(/[^a-z]/g, "");
        const service =
          raw === "aer"
            ? "AER"
            : ["tym", "tm"].includes(raw)
              ? "TYM"
              : ["ixb", "dxb"].includes(raw)
                ? "IxB"
                : raw === "saas"
                  ? "SaaS"
                  : raw === "raas"
                    ? "RaaS"
                    : "Otros";
        const fact = cs.includes("Facturable")
            ? true
            : cs.includes("No Facturables")
              ? false
              : null,
          carg =
            !cs.includes("Administrativas") && !cs.includes("Sin Asignación"),
          affect = !cs.includes("Optimización");
        m.total += h;
        m.people.add(name);
        m.svc[service] += h;
        m.weighted += h * weights[service];
        if (fact === true) m.fact += h;
        else if (fact === false) m.non += h;
        else m.unknown += h;
        m[carg ? "carg" : "nocarg"] += h;
        m[affect ? "affect" : "noaffect"] += h;
        const op = cs.includes("Inversión Operaciones") ? h : 0,
          com = cs.includes("Inversión Comercial") ? h : 0,
          prod = /inversion.*producto|inv.*producto/.test(cat) ? h : 0;
        m.invop += op;
        m.invcom += com;
        m.invprod += prod;
        if (!people.has(name))
          people.set(name, {
            name: d.recurso,
            area: d.area,
            months: Array(12).fill(null),
          });
        const p = people.get(name);
        if (!p.months[i])
          p.months[i] = {
            total: 0,
            fact: 0,
            non: 0,
            invop: 0,
            invcom: 0,
            invprod: 0,
            unknown: 0,
          };
        const pm = p.months[i];
        pm.total += h;
        if (fact === true) pm.fact += h;
        else if (fact === false) pm.non += h;
        else pm.unknown += h;
        pm.invop += op;
        pm.invcom += com;
        pm.invprod += prod;
      }
      monthly[i].cap = monthly[i].people.size * state.day * workdays(i);
    });
    const indices =
        kpiMonth < 0
          ? months.map((_, i) => i).filter((i) => valid[i])
          : valid[kpiMonth]
            ? [kpiMonth]
            : [],
      sum = (field) => indices.reduce((n, i) => n + monthly[i][field], 0),
      total = sum("total"),
      unknown = sum("unknown");
    return {
      monthly,
      valid,
      people,
      employeeNames,
      services,
      weights,
      indices,
      total,
      unknown,
      sum,
      normalize,
    };
  }
  function resourceRows() {
    const norm = (s) =>
      String(s || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim()
        .replace(/\s+/g, " ")
        .toUpperCase();
    const bandsByPerson = new Map();
    const addBand = (name, i, value) => {
      const k = norm(name),
        v = String(value || "").trim();
      if (!v || /^n[\/ ]?a$/i.test(v)) return;
      if (!bandsByPerson.has(k)) bandsByPerson.set(k, {});
      const b = bandsByPerson.get(k);
      if (b[i] && b[i] !== v) b[i] = "Revisar";
      else b[i] = v;
    };
    (state.resourceBands || []).forEach((p) =>
      (p.bandas || []).forEach((v, i) => addBand(p.recurso, i, v)),
    );
    months.forEach((_, i) => {
      const r = state.data[key(i)];
      if (r?.ok)
        for (const d of r.detalle || []) addBand(d.recurso, i, d.banda);
    });
    const map = new Map();
    months.forEach((_, i) => {
      const r = state.data[key(i)];
      if (!r || !r.ok || !Array.isArray(r.detalle)) return;
      r.detalle
        .filter((d) => !state.area || d.area === state.area)
        .forEach((d) => {
          // Identidad única persona + ID final. Categoría/tipo no crean otras filas.
          const k = JSON.stringify([norm(d.recurso), norm(d.proyecto)]);
          if (!map.has(k))
            map.set(k, {
              ...d,
              values: Array(12).fill(0),
              bands: {},
              categories: new Set(),
              types: new Set(),
              services: new Set(),
            });
          const row = map.get(k);
          row.values[i] += Number(d.horas) || 0;
          row.bands[i] = d.banda;
          if (d.categoria && d.categoria !== "Sin clasificación")
            row.categories.add(d.categoria);
          if (d.tipo && d.tipo !== "NA") row.types.add(d.tipo);
          if (d.servicio && d.servicio !== "NA") row.services.add(d.servicio);
        });
    });
    return Array.from(map.values())
      .map((row) => ({
        ...row,
        bands: bandsByPerson.get(norm(row.recurso)) || {},
        categoria:
          Array.from(row.categories).join(" / ") || "Sin clasificación",
        tipo: Array.from(row.types).join(" / ") || "NA",
        servicio: Array.from(row.services).join(" / ") || "NA",
      }))
      .sort(
        (a, b) =>
          a.recurso.localeCompare(b.recurso, "es") ||
          a.proyecto.localeCompare(b.proyecto, "es"),
      );
  }
  function gseBajaSet() {
    const n = (v) =>
        String(v || "")
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase()
          .trim()
          .replace(/\s+/g, " "),
      set = new Set(),
      isBaja = (v) => n(v) === "baja";
    for (const p of state.resourceBands || [])
      if ((p.bandas || []).some(isBaja)) set.add(n(p.recurso));
    months.forEach((_, i) => {
      const r = state.data[key(i)];
      if (r?.ok)
        for (const d of r.detalle || [])
          if (isBaja(d.banda)) set.add(n(d.recurso));
    });
    return set;
  }

  function overview() {
    const valid = months.map((_, i) => state.data[key(i)]?.ok),
      norm = (s) =>
        String(s || "")
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase()
          .replace(/\s+/g, " ")
          .trim();
    const areas = new Map(),
      people = new Set();
    let capacity = 0,
      total = 0,
      fact = 0,
      nonfact = 0,
      other = 0,
      factUnknown = false;
    months.forEach((_, i) => {
      const r = state.data[key(i)];
      if (!r?.ok) return;
      for (const a of r.areas || []) {
        if (!areas.has(a.area))
          areas.set(a.area, {
            name: a.area,
            months: Array(12).fill(null),
            people: new Set(),
          });
        const x = areas.get(a.area);
        x.months[i] = a;
        for (const p of a.personas || []) {
          x.people.add(norm(p.nombre));
          people.add(norm(p.nombre));
        }
        capacity += workdays(i) * state.day * (a.recursos || 0);
        total += a.horas || 0;
        if (a.categorias.Facturable === null) factUnknown = true;
        fact += a.categorias.Facturable || 0;
        nonfact += a.categorias["No Facturables"] || 0;
        other += a.categorias["Pre-Venta"] || 0;
      }
    });
    const list = Array.from(areas.values()),
      has = valid.some(Boolean),
      pct = (n, d) => (n == null ? null : d ? (n / d) * 100 : null),
      percentage = (n) => (n == null ? "NA" : num(n) + "%"),
      sumCat = (area, cat) =>
        area.months.some((a) => a?.categorias?.[cat] === null)
          ? null
          : area.months.reduce((n, a) => n + (a?.categorias?.[cat] || 0), 0),
      sumHours = (area) => area.months.reduce((n, a) => n + (a?.horas || 0), 0);

    const monthly = months.map((_, i) => aggregate(i));
    if (factUnknown) fact = null;
    return {
      valid,
      list,
      people,
      has,
      pct,
      percentage,
      sumCat,
      sumHours,
      monthly,
      capacity,
      total,
      fact,
      nonfact,
      other,
    };
  }
  function selectedArea() {
    const gseAreaMonth = selection.areaMonth;
    const monthly = months.map((_, i) => aggregate(i)),
      available = monthly.map((x, i) => (x ? i : -1)).filter((i) => i >= 0);
    const month = gseAreaMonth,
      indices = month < 0 ? available : [month],
      period = month < 0 ? "Todos los meses" : months[month],
      picked = indices.map((i) => monthly[i]).filter(Boolean),
      people = new Set();
    for (const i of indices) {
      const raw = state.data[key(i)];
      for (const d of raw?.detalle || [])
        if (d.area === state.area && d.horas > 0)
          people.add(
            String(d.recurso)
              .normalize("NFD")
              .replace(/[\u0300-\u036f]/g, "")
              .toLowerCase()
              .trim(),
          );
      for (const a of raw?.areas || [])
        if (a.area === state.area)
          for (const p of a.personas || [])
            people.add(
              String(p.nombre)
                .normalize("NFD")
                .replace(/[\u0300-\u036f]/g, "")
                .toLowerCase()
                .trim(),
            );
    }
    const m = picked.length
        ? {
            recursos: month < 0 ? people.size : picked[0].recursos,
            categorias: {
              "No Facturables": picked.some(
                (a) => a.categorias["No Facturables"] === null,
              )
                ? null
                : picked.reduce(
                    (n, a) => n + (a.categorias["No Facturables"] || 0),
                    0,
                  ),
            },
          }
        : null,
      cap = picked.length
        ? indices.reduce(
            (n, i) =>
              n +
              (monthly[i] ? workdays(i) * state.day * monthly[i].recursos : 0),
            0,
          )
        : null,
      annualCap = cap,
      hours = picked.reduce((n, a) => n + (a.horas || 0), 0),
      factUnknown = picked.some((a) => a.categorias.Facturable === null),
      fact = factUnknown
        ? null
        : picked.reduce((n, a) => n + (a.categorias.Facturable || 0), 0),
      ratio = (v, d) => (v == null || !d ? null : (v / d) * 100),
      fmtPct = (n) => (n == null ? "NA" : num(n) + "%");
    return {
      monthly,
      indices,
      period,
      picked,
      m,
      cap,
      annualCap,
      hours,
      fact,
      ratio,
      fmtPct,
    };
  }
  function percentResources() {
    const norm = (s) =>
        String(s || "")
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase()
          .trim(),
      byPerson = new Map(),
      valid = months.map((_, i) => state.data[key(i)]?.ok);
    months.forEach((_, i) => {
      if (!valid[i]) return;
      for (const d of state.data[key(i)].detalle || []) {
        if ((state.area && d.area !== state.area) || !(d.horas > 0)) continue;
        const k = norm(d.recurso);
        if (!byPerson.has(k))
          byPerson.set(k, {
            name: d.recurso,
            area: d.area,
            months: Array(12).fill(null),
          });
        const r = byPerson.get(k);
        if (!r.months[i]) r.months[i] = { fact: 0, total: 0 };
        r.months[i].total += Number(d.horas) || 0;
        const cs = gseKPICategories(d, norm);
        if (cs.includes("Facturable")) r.months[i].fact += Number(d.horas) || 0;
      }
    });
    return { byPerson, valid };
  }
  function hoursDetail() {
    const {
      hoursOpen: gseHoursOpen,
      hoursSearch: gseHoursSearch,
      hoursRole: gseHoursRole,
      hoursService: gseHoursService,
    } = selection;
    const norm = (s) =>
        String(s || "")
          .normalize("NFD")
          .replace(/[̀-ͯ]/g, "")
          .toLowerCase()
          .trim(),
      HIDDEN = ["TYM", "IxB", "SaaS", "RaaS"],
      ALL = ["AER", ...HIDDEN];
    const serviceOf = (d) => {
      const raw = norm(d.servicio).replace(/[^a-z]/g, "");
      return raw === "aer"
        ? "AER"
        : ["tym", "tm"].includes(raw)
          ? "TYM"
          : ["ixb", "dxb"].includes(raw)
            ? "IxB"
            : raw === "saas"
              ? "SaaS"
              : raw === "raas"
                ? "RaaS"
                : "Otros";
    };
    const blank = () => ({
        total: 0,
        AER: 0,
        TYM: 0,
        IxB: 0,
        SaaS: 0,
        RaaS: 0,
        svc: 0,
      }),
      valid = months.map(
        (_, i) =>
          state.data[key(i)]?.ok && Array.isArray(state.data[key(i)].detalle),
      ),
      byPerson = new Map(),
      sums = months.map(blank),
      roles = new Set();
    months.forEach((_, i) => {
      if (!valid[i]) return;
      for (const d of state.data[key(i)].detalle) {
        if (state.area && d.area !== state.area) continue;
        const h = Number(d.horas) || 0;
        if (!(h > 0)) continue;
        roles.add(d.area);
        if (gseHoursRole && d.area !== gseHoursRole) continue;
        const sv = serviceOf(d);
        if (gseHoursService && sv !== gseHoursService) continue;
        const k = norm(d.recurso);
        if (!byPerson.has(k))
          byPerson.set(k, {
            name: d.recurso,
            area: d.area,
            m: Array(12).fill(null),
          });
        const r = byPerson.get(k);
        if (!r.m[i]) r.m[i] = blank();
        r.m[i].total += h;
        sums[i].total += h;
        if (sv !== "Otros") {
          r.m[i][sv] += h;
          sums[i][sv] += h;
          if (sv !== "AER") {
            r.m[i].svc += h;
            sums[i].svc += h;
          }
        }
      }
    });
    const rows = Array.from(byPerson.values())
      .filter((r) => norm(r.name + " " + r.area).includes(norm(gseHoursSearch)))
      .sort(
        (a, b) =>
          a.area.localeCompare(b.area, "es") ||
          a.name.localeCompare(b.name, "es"),
      );
    const yearOf = (cells) =>
      cells.reduce((acc, c) => {
        if (c) ["total", "svc", ...ALL].forEach((f) => (acc[f] += c[f]));
        return acc;
      }, blank());
    const YEAR_COLS = ["total", "AER", "svc", ...HIDDEN],
      monthCols = (i) =>
        gseHoursOpen.has(i)
          ? ["total", "AER", "svc", ...HIDDEN]
          : ["total", "AER", "svc"];
    const titleOf = { total: "Total", svc: "Servicios" },
      label = (f) => titleOf[f] || f,
      round = (v) => Math.round(v * 100) / 100;
    return {
      norm,
      HIDDEN,
      ALL,
      blank,
      valid,
      byPerson,
      sums,
      roles,
      rows,
      yearOf,
      YEAR_COLS,
      monthCols,
      label,
      round,
    };
  }
  function monthlyRows() {
    const totals = months.map((_, i) => aggregate(i)),
      caps = totals.map((a, i) =>
        a && a.recursos != null ? workdays(i) * state.day * a.recursos : null,
      );
    const rows = [];
    const row = (label, values) =>
      rows.push([label, ...values.map((v) => (v == null ? "NA" : v))]);
    row(
      "Estado de consulta",
      months.map((_, i) => {
        const r = state.data[key(i)];
        return !r
          ? "Sin consultar"
          : r.pending
            ? "Leyendo…"
            : r.sinDatos
              ? "Sin registros"
              : r.ok
                ? r.parcial
                  ? "Parcial"
                  : "Disponible"
                : "ERROR";
      }),
    );
    row(
      "Inicio mes",
      months.map(
        (_, i) => "01/" + String(i + 1).padStart(2, "0") + "/" + state.year,
      ),
    );
    row(
      "Fin mes",
      months.map(
        (_, i) =>
          new Date(state.year, i + 1, 0).getDate() +
          "/" +
          String(i + 1).padStart(2, "0") +
          "/" +
          state.year,
      ),
    );
    row("Días festivos", state.holidays);
    row(
      "Días laborables",
      months.map((_, i) => workdays(i)),
    );
    row(
      "Recursos",
      totals.map((a) => (a ? a.recursos : null)),
    );
    row(
      "Horas al día",
      months.map(() => state.day),
    );
    row("Capacidad horas al mes", caps, false, true);
    row(
      "Total horas registradas",
      totals.map((a) => (a ? a.horas : null)),
      false,
      true,
    );
    cats.forEach((c) =>
      row(
        c,
        totals.map((a) => (a ? a.categorias[c] : null)),
      ),
    );
    const pct = (i, cs) =>
      totals[i] &&
      caps[i] > 0 &&
      cs.every((c) => totals[i].categorias[c] !== null)
        ? (cs.reduce((n, c) => n + (totals[i].categorias[c] || 0), 0) /
            caps[i]) *
          100
        : null;
    cats.forEach((c) =>
      row(
        "% " + c,
        months.map((_, i) => pct(i, [c])),
        true,
      ),
    );
    row(
      "Facturabilidad",
      months.map((_, i) =>
        pct(i, [
          "Facturable",
          "Pre-Venta",
          "Optimización",
          "Agentes Autónomos",
          "Inversión Comercial",
        ]),
      ),
      true,
      true,
    );
    row(
      "Capacidad",
      months.map((_, i) => {
        const p = pct(i, ["Sin Asignación"]);
        return p == null ? null : 100 - p;
      }),
      true,
      true,
    );
    row(
      "Clientes Internos",
      months.map((_, i) =>
        pct(i, [
          "Inversión Comercial",
          "Laboratorio",
          "Pre-Venta",
          "Internos",
          "Agentes Autónomos",
        ]),
      ),
      true,
      true,
    );
    return rows;
  }
  function kpiSummary() {
    const kpiMonth = selection.kpiMonth;
    const d = gseKPIMetrics(),
      { monthly, valid, people, employeeNames, services, indices, sum, total } =
        d,
      pct = (n, t) => (n == null || !t ? null : (n / t) * 100),
      f = (n) => (n == null ? "NA" : num(n)),
      p = (n) => (n == null ? "NA" : num(n) + "%"),
      period = kpiMonth < 0 ? "Todos los meses" : months[kpiMonth],
      latest = kpiMonth < 0 ? indices.at(-1) : kpiMonth,
      previous = latest > 0 && valid[latest - 1] ? monthly[latest - 1] : null,
      current = latest != null ? monthly[latest] : null,
      variation =
        current && previous
          ? pct(current.total - previous.total, previous.total)
          : null,
      annualTotal = monthly.reduce(
        (n, m, i) => n + (valid[i] ? m.total : 0),
        0,
      ),
      annualCapacity = monthly.reduce(
        (n, m, i) => n + (valid[i] ? m.cap : 0),
        0,
      ),
      annualFact = monthly.reduce((n, m, i) => n + (valid[i] ? m.fact : 0), 0),
      annualUnknown = monthly.some((m, i) => valid[i] && m.unknown > 0),
      fact = pct(sum("fact"), sum("cap")),
      maturity =
        pct(sum("weighted"), total) == null ? null : sum("weighted") / total;
    return {
      d,
      monthly,
      valid,
      people,
      employeeNames,
      services,
      indices,
      sum,
      total,
      pct,
      f,
      p,
      period,
      latest,
      variation,
      fact,
      maturity,
      annualFact,
      annualCapacity,
    };
  }
  return {
    kpiSummary,
    monthlyRows,
    overview,
    selectedArea,
    percentResources,
    hoursDetail,
    key,
    aggregate,
    workdays,
    categories: gseKPICategories,
    kpis: gseKPIMetrics,
    resourceRows,
    bajas: gseBajaSet,
  };
}
function baseMonth(job, mes) {
  if (!job.months[mes])
    job.months[mes] = { areas: new Map(), details: new Map() };
  return job.months[mes];
}
export function baseApply(job, r) {
  if (!r || !r.ok)
    throw new Error(
      (r && r.error) || "Sheets no devolvió un resultado válido.",
    );
  if (r.bandas && r.bandas.length) job.bandas = r.bandas;
  for (const entry of r.records || []) {
    if (job.seen.has(entry.id)) continue;
    job.seen.add(entry.id);
    const m = baseMonth(job, entry.mes),
      ak = entry.area;
    if (!m.areas.has(ak))
      m.areas.set(ak, {
        area: ak,
        horas: 0,
        categorias: {},
        people: new Map(),
      });
    const area = m.areas.get(ak);
    area.horas += entry.horas;
    const pk = entry.recurso;
    if (!area.people.has(pk))
      area.people.set(pk, { nombre: pk, horas: 0, baja: entry.baja });
    area.people.get(pk).horas += entry.horas;
    for (const cat of entry.categorias || [])
      area.categorias[cat] = (area.categorias[cat] || 0) + entry.horas;
    const dk = JSON.stringify([
      entry.recurso,
      entry.proyecto,
      entry.categoria,
      entry.tipo,
      entry.categorias || [],
    ]);
    if (!m.details.has(dk))
      m.details.set(dk, {
        recurso: entry.recurso,
        area: entry.area,
        banda: entry.banda,
        categoria: entry.categoria,
        tipo: entry.tipo,
        proyecto: entry.proyecto,
        servicio: entry.servicio || "NA",
        categorias: (entry.categorias || []).slice(),
        horas: 0,
      });
    m.details.get(dk).horas += entry.horas;
  }
  job.cursor = r.cursor;
  job.total = r.total;
  job.done = r.done;
  job.invalid += r.invalid || 0;
  job.unmatched += r.unmatched || 0;
  job.catalogoAviso = r.catalogoAviso || "";
}
export function baseSnapshot(job, last) {
  const data = {};
  for (let i = 0; i <= last; i++) {
    const mes = job.year + "-" + String(i + 1).padStart(2, "0"),
      m = job.months[mes];
    if (!m) {
      data[mes] = {
        ok: false,
        mes,
        pending: !job.done,
        sinDatos: job.done,
        error: job.done ? "Sin registros guardados para esta área y mes." : "",
      };
      continue;
    }
    const areas = Array.from(m.areas.values()).map((a) => {
      const categorias = Object.assign({}, a.categorias);
      categorias["Administrativo Operaciones"] =
        (categorias["Inversión Operaciones"] || 0) +
        (categorias["Inversión Comercial"] || 0);
      if (job.catalogoAviso)
        for (const c of [
          "Facturable",
          "Optimización",
          "Agentes Autónomos",
          "Continuos Improvement",
          "Laboratorio",
        ])
          categorias[c] = null;
      return {
        area: a.area,
        horas: a.horas,
        recursos: a.people.size,
        categorias,
        personas: Array.from(a.people.values()),
      };
    });
    data[mes] = {
      ok: true,
      mes,
      areas,
      detalle: Array.from(m.details.values()),
      catalogoAviso: job.catalogoAviso,
      source: "Registros disponibles en Sheets",
      parcial: !job.done,
    };
  }
  return data;
}
