// @ts-check
// Editor de hitos adicionales del proyecto: abre la ventana, guarda por API v1
// y avisa a la pantalla (onDone) para que se recargue.
import { collectRows } from "./milestones_model.js";
import { createDialog, createRow } from "./milestones_view.js";

const message = (/** @type {any} */ error) => (error && error.message ? error.message : error);

/** @param {ReturnType<typeof import("../data.js").createProjectData>} api */
export function createMilestoneController(api) {
  /** @type {any} */
  let session = null;

  function close() {
    if (session) session.dialog.overlay.remove();
    session = null;
  }

  async function loadTypes() {
    const data = await api.milestoneTypes();
    return (data && data.tipos) || [];
  }

  /** @param {string} type */
  const entriesOf = (type) => session.hitos.filter((/** @type {any} */ h) => h.tipo === type);

  function addRow() {
    const row = createRow(session.types, entriesOf, { remove: removeInDialog });
    session.rows.push(row);
    session.dialog.rows.append(row.node);
    return row;
  }

  /** @param {string} type @param {number} index */
  async function removeInDialog(type, index) {
    if (!window.confirm(`¿Eliminar esta entrada de "${type}"? Esta acción no se puede deshacer.`)) return;
    try {
      const result = await api.deleteMilestone(session.projectId, type, index);
      if (result && result.ok) {
        session.hitos = result.hitos;
        for (const row of session.rows) if (row.node.isConnected && row.typeValue() === type) row.paintExisting();
      } else {
        window.alert("Error al eliminar: " + (result && result.error ? result.error : "desconocido"));
      }
    } catch (error) {
      window.alert("Error del servidor: " + message(error));
    }
  }

  async function save() {
    const { dialog } = session;
    const checked = collectRows(session.rows.filter((/** @type {any} */ r) => r.node.isConnected).map((/** @type {any} */ r) => r.read()));
    if (checked.error) return dialog.showError(checked.error);
    dialog.showError("");
    dialog.busy(true);
    const current = session;
    try {
      for (const e of checked.ediciones || []) {
        const result = await api.editMilestone(current.projectId, e);
        if (!result || !result.ok) throw new Error("Error al editar: " + (result && result.error ? result.error : "desconocido."));
        current.hitos = result.hitos;
      }
      if (checked.nuevos && checked.nuevos.length) {
        const result = await api.saveMilestones(current.projectId, checked.nuevos);
        if (!result || !result.ok) throw new Error("Error al guardar: " + (result && result.error ? result.error : "desconocido. Revisa Ejecuciones en Apps Script."));
      }
    } catch (error) {
      if (session === current) {
        dialog.busy(false);
        dialog.showError(message(error));
      }
      return;
    }
    if (session !== current) return;
    close();
    current.onDone();
  }

  /** @param {string} projectId @param {any[]} hitos @param {() => void} onDone @param {any[]} types */
  function build(projectId, hitos, onDone, types) {
    const dialog = createDialog({ close, add: () => addRow(), save });
    session = { projectId, hitos, onDone, types, dialog, rows: [] };
    document.body.append(dialog.overlay);
    return addRow();
  }

  return {
    close,
    /** Alta de hitos nuevos (con tipos ya usados). */
    async open(/** @type {string} */ projectId, /** @type {any[]} */ hitos, /** @type {() => void} */ onDone) {
      close();
      let types = [];
      try {
        types = await loadTypes();
      } catch {
        types = [];
      }
      build(projectId, hitos || [], onDone, types);
    },
    /** Abre el editor con la entrada lista para cambiarse. */
    async edit(projectId, hitos, onDone, { tipo, indice, fechaISO, observacion }) {
      close();
      let types;
      try {
        types = await loadTypes();
      } catch {
        window.alert("No se pudo abrir el editor de hitos.");
        return;
      }
      const row = build(projectId, hitos || [], onDone, types);
      row.select(tipo);
      row.edit(tipo, indice, fechaISO, observacion);
    },
    /** Borrado directo desde la tarjeta de hitos. */
    async remove(/** @type {string} */ projectId, /** @type {string} */ tipo, /** @type {number} */ indice, /** @type {() => void} */ onDone) {
      if (!window.confirm(`¿Eliminar esta entrada de "${tipo}"? Esta acción no se puede deshacer.`)) return;
      try {
        const result = await api.deleteMilestone(projectId, tipo, indice);
        if (result && result.ok) onDone();
        else window.alert("Error al eliminar: " + (result && result.error ? result.error : "desconocido"));
      } catch (error) {
        window.alert("Error del servidor: " + message(error));
      }
    },
  };
}
