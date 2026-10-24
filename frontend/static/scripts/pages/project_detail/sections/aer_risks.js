import { risksModel } from "./aer_risks_model.js";
import { renderRisks, openRisk } from "./aer_risks_view.js";

const value = (id) => document.getElementById(id)?.value || "";
export function createAerRisks(api) {
  const bind = (env) => {
    const live = () => env.current();
    const publish = (risks) => {
      if (!risks) return;
      env.dashboard.riesgos = risks;
      if (env.active()) env.paint();
    };
    const methods = {
      open(uid = "") {
        return openRisk(env.dashboard, uid, methods);
      },
      openAction: env.openAction,
      async save(uid) {
        const modal = document.getElementById("aer-modal-back"),
          button = modal?.querySelector(".aer-actions .aer-btn.primary");
        if (button?.disabled) return;
        const saver = env.saving(button, "Guardando riesgo...");
        try {
          const result = await api.saveAerRisk(env.id, "guardar", {
            UID: uid,
            ID_Proyecto: env.id,
            Riesgo: value("ar-r"),
            Impacto: value("ar-i"),
            Probabilidad: value("ar-p"),
            Responsable: value("ar-resp"),
            Fecha_Limite: value("ar-f"),
            Estado: value("ar-e"),
            Accion: value("ar-a"),
            Notas: value("ar-n"),
          });
          if (!live()) return;
          if (!result?.ok) {
            if (modal?.isConnected)
              saver.error(result?.error || "No se pudo guardar.");
            return;
          }
          saver.ok("Riesgo guardado");
          if (modal?.isConnected) modal.remove();
          publish(result.riesgos);
        } catch (error) {
          if (live() && modal?.isConnected)
            saver.error(error?.message || String(error || "Error al guardar."));
        }
      },
      async clean() {
        if (!env.id) return;
        try {
          const result = await api.saveAerRisk(
            env.id,
            "limpiar-duplicados",
            {},
          );
          if (!live()) return;
          if (!result?.ok) {
            env.error(result?.error);
            return;
          }
          publish(result.riesgos);
          alert(
            Number(result.eliminados || 0) > 0
              ? `Se eliminaron ${result.eliminados} riesgo(s) duplicado(s).`
              : "No se encontraron riesgos duplicados.",
          );
        } catch (error) {
          if (live()) env.error(error);
        }
      },
      async remove(uid) {
        if (!confirm("¿Eliminar este riesgo?")) return;
        const modal = document.getElementById("aer-modal-back");
        try {
          const result = await api.saveAerRisk(env.id, "eliminar", { uid });
          if (!live()) return;
          if (!result?.ok) {
            env.error(result?.error);
            return;
          }
          if (modal?.isConnected) modal.remove();
          const response = await api.aerRisks(env.id);
          if (live() && response?.ok) publish(response.riesgos);
        } catch (error) {
          if (live()) env.error(error);
        }
      },
    };
    return methods;
  };
  return {
    bind,
    mount(target, env) {
      renderRisks(target, risksModel(env.dashboard), bind(env));
    },
  };
}
