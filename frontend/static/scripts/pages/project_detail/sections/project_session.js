import {
  selectAerAi,
  selectIxsAi,
  selectClockify,
  outdatedAer,
} from "./project_session_model.js";
import { aerError, ixsError, outdatedNotice } from "./project_session_view.js";

export function createProjectSession(api, views) {
  return {
    aer(data, env) {
      const target = document.getElementById("dashboard-proyecto-detalle");
      if (!target) return;
      if (!data?.ok) {
        aerError(target, data?.error);
        return;
      }
      env.styles.aer();
      env.aerAi(selectAerAi(env.aerAi(), data));
      env.aer(data);
      env.aerTab("ejecutivo");
      env.render.aer();
      if (outdatedAer(data)) outdatedNotice(target.querySelector(".aer-shell"));
    },
    async ixs(data, env) {
      const target = document.getElementById("dashboard-proyecto-detalle");
      if (!target) return;
      if (!data?.proyecto) {
        ixsError(target, data?.errorServidor);
        return;
      }
      env.clockify(selectClockify(env.clockify(), data.proyecto.id));
      env.ixs(data);
      env.ixsTab("resumen");
      env.globalId(data.proyecto.id);
      views.beeIxsEffort.selectProject(data);
      env.styles.ixs();
      env.render.ixs();
      if ((data.hitos || []).length && (data.historialCompleto || []).length)
        return;
      try {
        const result = await api.stages(data.proyecto.id);
        if (env.ixs() !== data || !result?.ok) return;
        data.hitos = result.hitos || [];
        data.historialCompleto = result.historialCompleto || [];
        data.suspensiones = result.suspensiones || [];
        const gantt = document.getElementById("ixs-gantt-historico");
        if (!gantt) return;
        if (env.ixsTab() === "planeacion") {
          views.beeIxsPlanning.paint();
          return;
        }
        views.beeIxsExecutive.updateTimeline(gantt, data);
      } catch (error) {
        const gantt = document.getElementById("ixs-gantt-historico");
        if (
          env.ixs() === data &&
          gantt &&
          !((data.hitos || []).length || (data.historialCompleto || []).length)
        )
          gantt.textContent =
            "No se pudieron cargar las etapas del histórico: " +
            (error?.message || error);
      }
    },
    ai(env) {
      const project = env.ixs();
      if (!project) return;
      env.styles.ai();
      env.ixsAi(selectIxsAi(env.ixsAi(), project));
      env.render.ai();
      env.aiLoads.sources();
      env.aiLoads.history();
      env.aiLoads.drive();
    },
    clientActions(env) {
      const project = env.ixs(),
        id = project?.proyecto?.id,
        target = document.getElementById("ixs-tab-contenido");
      if (!id || !target) return;
      env.styles.aer();
      return views.beeIxsClientActions.load({
        project,
        target,
        cache: env.cache,
        tab: env.ixsTab(),
        current: (key) =>
          env.ixs()?.proyecto.id === key &&
          ["cliente", "acciones"].includes(env.ixsTab()) &&
          !!document.querySelector("#dashboard-proyecto-detalle .ixs-shell"),
        apply: (result) => {
          env.aer(result);
          const ai = env.aerAi();
          ai.id = id;
          ai.accionesPartes = result.partes || [];
          env.render.aerTab();
        },
      });
    },
  };
}
