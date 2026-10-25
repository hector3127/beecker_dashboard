import {
  applyResourceStates,
  isoDate,
  suggestedDates,
} from "./ixs_support_model.js";

export function createIxsSupport(api, views) {
  return {
    suggestedDates,
    editMilestone(index, env) {
      const project = env.project();
      if (env.tab() !== "planeacion" || !project) return;
      const milestone = (project.hitosAdicionales || [])[index];
      if (!milestone) return;
      env.selectMilestones(project);
      env.edit(
        milestone.tipo,
        milestone.indice,
        isoDate(milestone.fecha),
        milestone.observacion || "",
      );
    },
    async resources(env) {
      const project = env.project();
      if (
        !project ||
        project._resourceStatesLoaded ||
        project._resourceStatesLoading
      )
        return;
      project._resourceStatesLoading = true;
      try {
        const result = await api.resources(project.proyecto.id);
        project._resourceStatesLoading = false;
        if (!result?.ok) return;
        project._resourceStatesLoaded = true;
        applyResourceStates(project, result);
        if (env.project() !== project) return;
        switch (env.tab()) {
          case "esfuerzo": {
            const table = document.querySelector(".ixs-effort-compact");
            if (table) views.beeIxsEffort.updateResources(table, project);
            break;
          }
          case "planeacion":
            views.beeIxsPlanning.paint();
            break;
          case "resumen": {
            const table = document.querySelector("[data-resource-workload]");
            if (table)
              table.replaceWith(views.beeIxsExecutive.resourceTable(project));
            break;
          }
        }
      } catch {
        project._resourceStatesLoading = false;
      }
    },
  };
}
