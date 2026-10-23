import { planningEditor } from "./ixs_planning_editor_view.js";

export function createPlanningEditor(api) {
  let session;
  function close() {
    session?.view.modal.remove();
    session = undefined;
  }
  async function submit(owner, deleting = false, event) {
    event?.preventDefault();
    if (session !== owner || owner.busy || !owner.current()) return;
    if (deleting && !window.confirm("¿Eliminar este registro?")) return;
    const { view, type, id, uid } = owner;
    const payload = { idProyecto: id, uid };
    new FormData(view.form).forEach((value, key) => {
      payload[key] = value;
    });
    owner.busy = true;
    view.saveButton.disabled = true;
    if (view.deleteButton) view.deleteButton.disabled = true;
    if (!deleting) view.saveButton.textContent = "Guardando…";
    const current = () =>
      session === owner && owner.current() && view.form.isConnected;
    try {
      const result = deleting
        ? await api.deletePlan(type, id, uid)
        : await api.savePlan(type, payload);
      if (!current()) return;
      if (!result || !result.ok) {
        view.error.textContent =
          result?.error ||
          (deleting ? "Error al eliminar." : "Error al guardar.");
        return;
      }
      close();
      owner.saved(result);
    } catch (error) {
      if (current()) view.error.textContent = error?.message || String(error);
    } finally {
      owner.busy = false;
      view.saveButton.disabled = false;
      if (view.deleteButton) view.deleteButton.disabled = false;
      view.saveButton.textContent = "Guardar";
    }
  }
  return {
    close,
    open(type, uid, initialType, state, lifecycle) {
      close();
      const owner = {
        type,
        uid,
        id: state.proyectoId,
        current: lifecycle.current,
        saved: lifecycle.saved,
        busy: false,
      };
      session = owner;
      owner.view = planningEditor(type, uid, initialType, state, {
        close,
        save: (event) => submit(owner, false, event),
        delete: () => submit(owner, true),
      });
    },
  };
}
