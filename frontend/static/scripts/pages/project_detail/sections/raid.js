// @ts-check
// Gestión RAID: lee los registros por API v1, conserva la última vista si
// Azure falla y atiende filtros y detalle. El alta sigue en el script anterior.
import { buildShell, detailDrawer, fillSections, paintHealth, paintMatrix, paintNotice, paintOptions, paintPeople, paintStages, paintSummary, paintTable, toggleAttention } from "./raid_view.js";
import { filterRows, iteration, normalizeSeverity, uniqueValues } from "./raid_model.js";

/** @param {{raidRegistry: (id: string, force: boolean) => Promise<any>}} api */
export function createRaidController(api) {
  const state = { projectId: "", rows: /** @type {any[]} */ ([]), notice: "", requestId: 0 };
  /** @type {HTMLElement | null} */
  let root = null;
  /** @type {any} */
  let data = null;
  /** @type {any} */
  let guards = null;

  const live = () => !!root && root.isConnected && guards.current(data) && guards.active();
  const value = (/** @type {string} */ id) => /** @type {HTMLInputElement | null} */ (root && root.querySelector("#" + id))?.value || "";
  const closeDetail = () => document.getElementById("ixs-raid-detail-overlay")?.remove();
  const openDetail = (/** @type {number} */ id) => {
    const row = state.rows.find((x) => Number(x.id) === Number(id));
    if (!row) return;
    closeDetail();
    document.body.append(detailDrawer(row, closeDetail));
  };
  const handlers = { detail: openDetail };

  function filter() {
    if (!root) return;
    const rows = filterRows(state.rows, { tipo: value("ixs-raid-filter-tipo"), estado: value("ixs-raid-filter-estado"), persona: value("ixs-raid-filter-persona"), iter: value("ixs-raid-filter-iteracion"), q: value("ixs-raid-filter-search") });
    paintTable(root, state.rows, rows, handlers);
  }

  function paint() {
    if (!root) return;
    const rows = state.rows;
    paintSummary(root, rows, handlers);
    paintHealth(root, rows);
    paintMatrix(root, rows);
    paintStages(root, rows);
    paintPeople(root, rows);
    paintOptions(root, "ixs-raid-filter-estado", uniqueValues(rows, "estado"), "Todos los estados");
    paintOptions(root, "ixs-raid-filter-persona", uniqueValues(rows, "asignadoA"), "Todos los responsables");
    paintOptions(root, "ixs-raid-filter-iteracion", uniqueValues(rows, "iterationPath").map(iteration), "Todas las iteraciones");
    paintNotice(root, state.notice || "Origen: Azure DevOps · Se muestran únicamente los registros del proyecto seleccionado.", !!state.notice && /última consulta|consulta anterior/i.test(state.notice));
    filter();
  }

  /** @param {boolean} [force] */
  async function load(force = false) {
    if (!root || !data) return;
    const id = data.proyecto.id;
    const request = ++state.requestId;
    const keepView = state.projectId === id && state.rows.length > 0;
    state.projectId = id;
    if (!keepView) fillSections(root, "Consultando Azure DevOps…");
    else {
      const note = root.querySelector("#ixs-raid-notice");
      if (note) note.textContent = "Actualizando desde Azure DevOps… Se conserva la última vista completa.";
    }
    const current = () => request === state.requestId && live();
    /** @param {string} text */
    const fail = (text, keptText = "") => {
      if (keepView) {
        state.notice = keptText;
        paint();
      } else if (root) fillSections(root, text, "#c52e48");
    };
    try {
      const result = await api.raidRegistry(id, !!force);
      if (!current()) return;
      if (!result || !result.ok) {
        const message = (result && result.error) || "No se obtuvo información.";
        fail(message, `⚠ No se pudo actualizar Azure: ${message}. Se conservan los datos de la consulta anterior.`);
        return;
      }
      state.rows = Array.isArray(result.registros) ? result.registros.map(normalizeSeverity) : [];
      state.notice = result.aviso || "";
      paint();
    } catch (error) {
      if (request !== state.requestId) return;
      const message = (error instanceof Error && error.message) || String(error);
      fail(message, `⚠ Azure no respondió: ${message}. Se conserva la consulta anterior.`);
    }
  }

  return {
    /**
     * @param {HTMLElement} target @param {any} project
     * @param {{current: (p: any) => boolean, active: () => boolean}} lifecycle
     * @param {{create: (type: string) => void}} hooks
     */
    mount(target, project, lifecycle, hooks) {
      closeDetail();
      data = project;
      guards = lifecycle;
      root = buildShell({
        create: hooks.create,
        sync: () => load(true),
        filter,
        toggle: (button) => root && toggleAttention(/** @type {HTMLElement} */ (root.querySelector("#ixs-raid-atencion")), button, state.rows.length),
      });
      target.replaceChildren(root);
      load(false);
    },
    reload: (/** @type {boolean} */ force) => load(force),
  };
}
