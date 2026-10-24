import { resourcesModel } from "./aer_resources_model.js";
import { renderResources, openEvaluation } from "./aer_resources_view.js";

const fields = {
  Recurso: "rec",
  Evaluador: "eval",
  Fecha_Evaluacion: "fecha",
  Proxima_Evaluacion: "prox",
  Calidad: "cal",
  Cumplimiento: "cum",
  Comunicacion: "comu",
  Colaboracion: "col",
  Autonomia: "aut",
  Comentario: "com",
  Plan_Accion: "plan",
};
export function createAerResources(api) {
  const bind = (env) => {
    const publish = (result) => {
      env.dashboard.evaluaciones = result.evaluaciones || { filas: [] };
      if (env.active()) env.paint();
    };
    const actions = {
      select(value) {
        env.selected(value);
        if (env.active()) env.paint();
      },
      open(uid = "") {
        return openEvaluation(env.dashboard, uid, actions);
      },
      async save(uid) {
        const modal = document.getElementById("aer-modal-back"),
          button = modal?.querySelector(".aer-actions .primary");
        if (button?.disabled) return;
        const payload = {
          UID: uid,
          ID_Proyecto: env.id,
          ...Object.fromEntries(
            Object.entries(fields).map(([key, id]) => [
              key,
              document.getElementById(`ae-${id}`)?.value || "",
            ]),
          ),
        };
        const saver = env.saving(button, "Guardando evaluación...");
        try {
          const result = await api.saveAerEvaluation(
            env.id,
            "guardar",
            payload,
          );
          if (!env.current()) return;
          if (!result?.ok) {
            if (modal?.isConnected)
              saver.error(result?.error || "No se pudo guardar.");
            return;
          }
          env.selected(payload.Recurso);
          saver.ok("Evaluación guardada");
          if (modal?.isConnected) modal.remove();
          publish(result);
        } catch (error) {
          if (env.current() && modal?.isConnected)
            saver.error(error?.message || String(error || "Error al guardar."));
        }
      },
      async remove(uid) {
        if (!confirm("¿Eliminar esta evaluación?")) return;
        const modal = document.getElementById("aer-modal-back");
        try {
          const result = await api.saveAerEvaluation(env.id, "eliminar", {
            uid,
          });
          if (!env.current()) return;
          if (!result?.ok) {
            env.error(result?.error);
            return;
          }
          if (modal?.isConnected) modal.remove();
          publish(result);
        } catch (error) {
          if (env.current()) env.error(error);
        }
      },
    };
    return actions;
  };
  return {
    bind,
    mount(target, env) {
      const model = resourcesModel(env.dashboard, env.selected());
      env.selected(model.selected);
      renderResources(target, model, env.dashboard, bind(env));
    },
  };
}
