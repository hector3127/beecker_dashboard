import { riskPayload } from "./generic_risk_model.js";
import { riskDialog } from "./generic_risk_view.js";

export function createGenericRisk(api, hooks) {
  let session = null;
  function close() {
    session?.dialog.overlay.remove();
    session = null;
  }
  async function save() {
    const active = session;
    if (!active || active.saving || !hooks.current(active.project)) return;
    const payload = riskPayload(active.dialog.values());
    if (!payload.descripcion) {
      active.dialog.message("Falta la descripción del riesgo.");
      return;
    }
    active.dialog.message("");
    active.saving = true;
    active.dialog.busy(true);
    const current = () =>
      session === active &&
      active.dialog.overlay.isConnected &&
      hooks.current(active.project);
    let result;
    try {
      result = await api.saveManualRisk(active.project, payload);
    } catch (error) {
      if (current()) {
        active.dialog.message(
          "Error del servidor: " + (error?.message || error),
        );
        active.dialog.busy(false);
        active.saving = false;
      }
      return;
    }
    if (!current()) return;
    active.dialog.busy(false);
    active.saving = false;
    if (!result || !result.ok) {
      active.dialog.message(
        "Error al guardar: " + (result?.error || "desconocido."),
      );
      return;
    }
    close();
    hooks.reload();
  }
  return {
    close,
    save,
    open(project) {
      close();
      const dialog = riskDialog({ close, save });
      session = { project, dialog, saving: false };
      document.body.append(dialog.overlay);
    },
  };
}
