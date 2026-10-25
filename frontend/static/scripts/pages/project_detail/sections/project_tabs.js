import { placeholder } from "./project_tabs_view.js";

// Adapters expose the existing state while project initialization is extracted.
export function createProjectTabs(views, aerFallback) {
  return {
    aer(env) {
      const shared =
        ["cliente", "acciones"].includes(env.ixsTab()) &&
        !!document.querySelector("#dashboard-proyecto-detalle .ixs-shell");
      const target = document.getElementById(
          shared ? "ixs-tab-contenido" : "aer-tab-content",
        ),
        project = env.aer();
      if (!target || !project) return;
      if (shared) env.aerTab(env.ixsTab());
      const tab = env.aerTab();
      switch (tab) {
        case "ejecutivo":
          return views.beeProjectExecutive(target, project, env.selectAer);
        case "planeacion":
          return views.beeAerPlanning.mount(target, env.aerContexts.planning());
        case "esfuerzo":
          return views.beeAerEffort.mount(target, env.aerContexts.effort());
        case "riesgos":
          return views.beeAerRisks.mount(target, env.aerContexts.risks());
        case "acciones":
          return views.beeProjectActions.mount(
            target,
            env.aerContexts.actions(),
          );
        case "recursos":
          return views.beeAerResources.mount(
            target,
            env.aerContexts.resources(),
          );
        case "ia":
          return views.beeAerAiPresentation.mount(target, env.aerContexts.ai());
        case "cliente":
          return views.beeProjectClient.mount(target, project, {
            family: shared ? "ixs" : "aer",
            current: () => env.aer() === project,
            active: () => env.aerTab() === "cliente" && target.isConnected,
          });
        default:
          return aerFallback(target, project, env.selectAer);
      }
    },
    ixs(env) {
      const target = document.getElementById("ixs-tab-contenido"),
        project = env.ixs();
      if (!target || !project) return;
      const tab = env.ixsTab(),
        lifecycle = {
          current: (candidate) => env.ixs() === candidate,
          active: () => env.ixsTab() === tab,
        };
      switch (tab) {
        case "ia":
          return env.openAi();
        case "comunicacion":
          return views.beeIxsCommunication.mount(target, project, lifecycle);
        case "planeacion": {
          const state = env.ixsStates();
          return views.beeIxsPlanning.mount(
            target,
            project,
            state.planning,
            state.planningAzure,
            {
              ...lifecycle,
              resources: env.resources,
              syncAzure: env.syncPlanningAzure,
              actions: env.planningActions,
            },
          );
        }
        case "recursos":
          return views.beeIxsResources.mount(target, project, lifecycle);
        case "esfuerzo":
          env.resources();
          return views.beeIxsEffort.mount(target, project, lifecycle);
        case "azure":
          return views.beeIxsAzureTab.mount(
            target,
            project,
            env.ixsStates().azure,
            { ...lifecycle, sync: env.syncAzure },
          );
        case "riesgos":
          return views.beeIxsRaid.mount(target, project, lifecycle, {
            create: env.createRaid,
          });
        case "cliente":
        case "acciones":
          return env.loadClientActions();
        case "resumen":
          env.resources();
          return views.beeIxsExecutive.mount(target, project, lifecycle);
        default:
          return placeholder(target, tab, {
            select: env.selectIxs,
            previous: env.previous,
          });
      }
    },
  };
}
