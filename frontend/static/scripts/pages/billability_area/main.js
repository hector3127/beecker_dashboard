import { apiGet, apiSend } from "#app/data/api-client.js";
import { months, createModel, baseApply, baseSnapshot } from "./model.js";
import { shell, render as draw, byId } from "./view.js";
import { download } from "./ui.js";

const state = {
  token: 0,
  data: {},
  year: Number(byId("gse-host").dataset.year) || new Date().getFullYear(),
  area: "",
  areaList: [],
  source: "sheet",
  day: 8,
  holidays: [],
  rows: [],
  busy: false,
};
const selection = {
  section: "general",
  expanded: new Set(),
  displayPercent: false,
  peopleMonth: -1,
  areaMonth: -1,
  areaPercent: false,
  areaCollapsed: new Set(),
  kpiPerson: "",
  kpiMonth: -1,
  kpiTarget: 80,
  percentSearch: "",
  hoursOpen: new Set(),
  hoursSearch: "",
  hoursRole: "",
  hoursService: "",
  detailPage: 0,
  detailSearch: "",
  detailBand: new Date().getMonth(),
};
const model = createModel(state, selection),
  key = model.key;
const root = "screens/facturabilidad/area/";
const read = async (path, params) =>
  (await apiGet(root + path + "/", params, { timeout: 90000 })).data;
const write = async (path, data) =>
  (await apiSend("POST", root + path + "/", data, { timeout: 90000 })).data;
let areasReady = false;
const loadedGSE = new Map();
function loadedGSEKey(area) {
  return JSON.stringify([state.year, state.source, area]);
}
function keepLoadedGSE() {
  if (state.loadedArea !== undefined && Object.keys(state.data).length)
    loadedGSE.set(loadedGSEKey(state.loadedArea), {
      data: state.data,
      bandas: state.resourceBands || [],
      area: state.loadedArea,
    });
}
function applyLoadedGSE(area) {
  keepLoadedGSE();
  const snapshot =
    loadedGSE.get(loadedGSEKey("")) || loadedGSE.get(loadedGSEKey(area));
  if (!snapshot) {
    state.data = {};
    state.resourceBands = [];
    state.loadedArea = undefined;
    return false;
  }
  state.data = snapshot.data;
  state.resourceBands = snapshot.bandas;
  state.loadedArea = snapshot.area;
  return true;
}

const actions = {
  set(name, value, focus) {
    selection[name] = value;
    render(focus);
  },
  toggle(name, value) {
    const set = selection[name];
    set.has(value) ? set.delete(value) : set.add(value);
    render();
  },
  holiday(i, value) {
    state.holidays[i] = Math.min(31, Math.max(0, Number(value) || 0));
    render();
  },
  day(value) {
    state.day = Math.min(24, Math.max(1, Number(value) || 8));
    render();
  },
  hoursAll(open) {
    selection.hoursOpen.clear();
    if (open) months.forEach((_, i) => selection.hoursOpen.add(i));
    render();
  },
  section(section) {
    selection.section = section;
    if (section === "detail") {
      selection.detailSearch = "";
      selection.detailPage = 0;
      const available = months
        .map((_, i) => i)
        .filter((i) => state.data[key(i)]?.ok);
      selection.detailBand = available.length
        ? available.at(-1)
        : new Date().getMonth();
    }
    render();
  },
  area(value) {
    if (state.busy) return;
    state.area = value;
    const available = applyLoadedGSE(value);
    render();
    byId("gse-status").textContent = available
      ? "Mostrando el área con los datos ya cargados."
      : "Esta área todavía no se ha consultado. Pulsa Consultar año.";
  },
  load(force) {
    if (!areasReady) {
      loadAreas();
      return;
    }
    load(force);
  },
  csv() {
    download(
      [["Concepto", ...months], ...state.rows],
      "GSE-" + state.year + ".csv",
    );
  },
  ids() {
    obtainIDs();
  },
};
function render(focus) {
  draw(state, selection, model, actions, focus);
}
async function loadAreas() {
  const token = state.token;
  for (const id of ["gse-area", "gse-load", "gse-refresh"])
    byId(id).disabled = true;
  byId("gse-status").textContent = "Cargando áreas de Bandas/rol…";
  try {
    const result = await read("areas");
    if (token !== state.token) return;
    if (!result.ok) throw new Error(result.error);
    state.areaList = result.areas;
    areasReady = true;
    render();
    byId("gse-status").textContent =
      "Selecciona el área y pulsa Consultar año. Aún no se han solicitado horas de Clockify.";
  } catch (error) {
    if (token === state.token)
      byId("gse-status").textContent = error.message || String(error);
  } finally {
    if (token === state.token)
      for (const id of ["gse-area", "gse-load", "gse-refresh"])
        byId(id).disabled = false;
  }
}
async function obtainIDs() {
  if (state.busy) return;
  const token = state.token,
    button = document.getElementById("gse-ids"),
    status = document.getElementById("gse-status");
  const month =
    String(document.getElementById("gse-year").value) +
    "-" +
    String(Number(document.getElementById("gse-detail").value) + 1).padStart(
      2,
      "0",
    );
  state.busy = true;
  button.disabled = true;
  let reportOnly = false;
  try {
    let r;
    do {
      status.textContent = "Obteniendo IDs Clockify de Bandas/rol…";
      r = await write("ids", { mes: month, solo_reporte: reportOnly });
      if (token !== state.token) return;
      if (r.pending) {
        reportOnly = true;
        status.textContent =
          "Buscando IDs en el reporte · " +
          r.records +
          " registros · página " +
          r.page;
        await new Promise((resolve) => setTimeout(resolve, 300));
      }
    } while (r.pending);
    if (!r.ok) throw new Error(r.error);
    status.textContent =
      "IDs guardados: " +
      r.guardados +
      " · Pendientes: " +
      r.pendientes.length +
      ". " +
      r.aviso +
      " Ahora pulsa Consultar año.";
    document.getElementById("gse-errors").textContent = "";
  } catch (e) {
    if (token === state.token)
      status.textContent = "No se pudieron obtener IDs: " + (e.message || e);
  } finally {
    if (token === state.token) {
      state.busy = false;
      button.disabled = false;
    }
  }
}
async function rpc(month, force) {
  const source = state.source,
    area = state.area,
    year = state.year;
  const result = await read("mes", {
    mes: month,
    fuente: source,
    actualizar: force ? "1" : "0",
    area,
  });
  if (
    result?.ok &&
    !result.pending &&
    state.source === source &&
    state.area === area &&
    state.year === year
  )
    state.data[month] = result;
  return result;
}
let baseJob = null;
function basePublish(job, last) {
  state.resourceBands = job.bandas || [];
  state.data = baseSnapshot(job, last);
  state.loadedArea = job.area;
  keepLoadedGSE();
  render();
}
async function loadBaseBlocks(year, area, force, token, last) {
  const signature = JSON.stringify([year, area]);
  if (!baseJob || baseJob.signature !== signature || force) {
    document.getElementById("gse-status").textContent = force
      ? "Actualizando desde la base…"
      : "Buscando resultado guardado…";
    let cached;
    try {
      cached = await (force
        ? write("cache", { anio: year, area, borrar: true })
        : read("cache", { anio: year, area }));
    } catch (e) {
      cached = null;
    }
    if (token !== state.token) return;
    if (!force && cached?.cached) {
      state.data = cached.data;
      state.resourceBands = cached.bandas || [];
      state.loadedArea =
        cached.scopeArea === undefined ? area : cached.scopeArea;
      keepLoadedGSE();
      render();
      document.getElementById("gse-status").textContent =
        "Resultado desde caché · guardado " +
        new Date(cached.savedAt).toLocaleString("es-MX") +
        ". Pulsa Actualizar sin caché para leer cambios recientes.";
      return;
    }
  }
  if (force || !baseJob || baseJob.signature !== signature)
    baseJob = {
      signature,
      year,
      area,
      cursor: 0,
      total: null,
      done: false,
      seen: new Set(),
      months: {},
      invalid: 0,
      unmatched: 0,
      catalogoAviso: "",
      flight: null,
    };
  const job = baseJob;
  while (!job.done) {
    if (token !== state.token) return;
    document.getElementById("gse-status").textContent =
      "Leyendo Sheets · " +
      job.cursor.toLocaleString("es-MX") +
      " / " +
      (job.total == null ? "…" : job.total.toLocaleString("es-MX")) +
      " filas · resultados parciales…";
    if (!job.flight) {
      job.flight = read("lote", {
        anio: year,
        area,
        cursor: job.cursor,
        total: job.total,
        actualizar: force && job.cursor === 0 ? "1" : "0",
      })
        .then((r) => {
          baseApply(job, r);
          return r;
        })
        .finally(() => {
          job.flight = null;
        });
    }
    await job.flight;
    if (token !== state.token) return;
    basePublish(job, last);
  }
  if (token !== state.token) return;
  basePublish(job, last);
  if (!job.cacheSaved) {
    job.cacheSaved = true;
    const snapshot = {
      data: state.data,
      bandas: state.resourceBands || [],
      total: job.total,
    };
    write("cache", { anio: year, area, resultado: snapshot })
      .then((r) => {
        if (!r?.ok) job.cacheSaved = false;
      })
      .catch(() => {
        job.cacheSaved = false;
      });
  }
  document.getElementById("gse-status").textContent =
    "Base leída · " +
    job.total.toLocaleString("es-MX") +
    " filas revisadas. Totales de los registros guardados; no se consultó Clockify." +
    (job.invalid ? " " + job.invalid + " duraciones inválidas omitidas." : "") +
    (job.unmatched
      ? " " + job.unmatched + " registros no coinciden con Bandas/rol."
      : "");
}
async function load(force) {
  if (state.busy) return;
  const year = Number(document.getElementById("gse-year").value);
  if (!Number.isInteger(year) || year < 2000 || year > 2100) return;
  const src = document.getElementById("gse-source").value;
  keepLoadedGSE();
  if (year !== state.year || src !== state.source) {
    state.data = {};
    state.resourceBands = [];
  }
  if (year !== state.year) {
    state.holidays =
      year === 2026 ? [1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1] : Array(12).fill(0);
    document
      .querySelectorAll("[data-holiday]")
      .forEach((x) => (x.value = state.holidays[Number(x.dataset.holiday)]));
  }
  state.year = year;
  state.source = src;
  if (
    !force &&
    applyLoadedGSE(state.area) &&
    Object.values(state.data).every((r) => !r.pending && !r.parcial)
  ) {
    render();
    document.getElementById("gse-status").textContent =
      "Mostrando los datos ya cargados. Los filtros utilizan los datos guardados.";
    return;
  }
  if (force) {
    for (const k of Array.from(loadedGSE.keys())) {
      const v = JSON.parse(k);
      if (v[0] === year && v[1] === src) loadedGSE.delete(k);
    }
    state.data = {};
    state.resourceBands = [];
  }
  state.loadedArea = state.area;
  state.busy = true;
  const token = ++state.token;
  document.getElementById("gse-load").disabled = true;
  document.getElementById("gse-refresh").disabled = true;
  document.getElementById("gse-area").disabled = true;
  const now = new Date(),
    last =
      year === now.getFullYear()
        ? now.getMonth()
        : year < now.getFullYear()
          ? 11
          : -1;
  try {
    if (state.source === "sheet") {
      await loadBaseBlocks(year, state.area, force, token, last);
      return;
    }
    for (let i = 0; i <= last; i++) {
      if (token !== state.token) return;
      if (!force && state.data[key(i)]?.ok) continue;
      document.getElementById("gse-status").textContent =
        "Consultando " + months[i] + " " + year + "…";
      let r;
      do {
        try {
          r = await rpc(key(i), force);
        } catch (e) {
          r = { ok: false, error: e.message || String(e) };
        }
        if (token !== state.token) return;
        if (r && r.pending) {
          document.getElementById("gse-status").textContent =
            "Consultando " +
            months[i] +
            " " +
            year +
            " · " +
            r.records +
            " registros recuperados · página " +
            r.page +
            "…";
          await new Promise((resolve) => setTimeout(resolve, 300));
        }
      } while (r && r.pending);
      if (token !== state.token) return;
      state.data[key(i)] = r;
      render();
    }
    document.getElementById("gse-status").textContent =
      "Consulta terminada. Revisa los errores mensuales debajo. Clockify reutiliza la caché durante una hora.";
  } catch (e) {
    if (token === state.token)
      document.getElementById("gse-status").textContent =
        "Error consultando: " + (e.message || String(e));
  } finally {
    if (token === state.token) {
      state.busy = false;
      document.getElementById("gse-area").disabled = false;
      document.getElementById("gse-load").disabled = false;
      document.getElementById("gse-refresh").disabled = false;
    }
  }
}

if (location.hash === "#capacidad-instalada")
  location.replace("/capacidad-instalada/" + location.search);
else {
  state.holidays =
    state.year === 2026
      ? [1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1]
      : Array(12).fill(0);
  shell(state, actions);
  render();
  loadAreas();
}
window.addEventListener("pagehide", () => {
  state.token++;
  state.busy = false;
});
