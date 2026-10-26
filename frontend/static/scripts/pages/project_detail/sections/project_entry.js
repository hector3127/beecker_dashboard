import { projectParams, metadata, family } from "./project_entry_model.js";
import * as view from "./project_entry_view.js";

export function createProjectEntry(api) {
  let request = 0;
  const params = () =>
    projectParams(
      window.location.search,
      document.getElementById("project-context")?.textContent,
    );
  const controller = {
    mount(env) {
      const target = document.getElementById("view-container");
      const template = document.getElementById("tpl-dashboard");
      if (!target || !template) return;
      target.replaceChildren(template.content.cloneNode(true));
      return controller.start(env);
    },
    async start(env) {
      const id = params().get("proyecto");
      if (!id) return controller.startCompatibility(env);
      const refresh = document.getElementById("btn-refresh");
      if (refresh) refresh.onclick = () => controller.load(env);
      try {
        const data = await api.filters();
        controller.populate(data, env);
        view.selectProject(params().get("proyecto"));
      } catch (error) {
        console.error(
          "No se pudieron cargar los filtros del dashboard:",
          error,
        );
      }
      return controller.load(env);
    },
    async startCompatibility(env) {
      const initial = params();
      if (!initial.get("proyecto") && !initial.get("cuenta")) return;
      const refresh = document.getElementById("btn-refresh");
      if (refresh) refresh.onclick = () => controller.load(env);
      try {
        const data = await api.filters();
        controller.populate(data, env);
        // Read parameters after the filter response, as the previous entry did.
        const account = params().get("cuenta");
        if (account) view.selectAccount(account);
        const id = params().get("proyecto");
        if (id) view.selectProject(id);
      } catch (error) {
        console.error(
          "No se pudieron cargar los filtros del dashboard:",
          error,
        );
      }
      return controller.load(env);
    },
    populate(data, env) {
      if (
        !data ||
        !document.getElementById("f-proyecto") ||
        !document.getElementById("f-cliente")
      )
        return;
      env.metadata(metadata(data));
      view.populate(data, () => controller.load(env), env.clientChanged);
    },
    async load(env) {
      const token = ++request;
      env.invalidatePrevious();
      const id =
        document.getElementById("f-proyecto")?.value || "Todos los proyectos";
      if (id === "Todos los proyectos") return env.previousLoad();
      document.body.classList.remove("bee-account-mode");
      const general = document.getElementById("dashboard-general");
      const target = document.getElementById("dashboard-proyecto-detalle");
      if (general) general.style.display = "none";
      const selected =
        document.getElementById("f-proyecto")?.selectedOptions?.[0];
      if (target) view.loading(target, selected?.textContent || id);
      const active = () => token === request && (!target || target.isConnected);
      const kind = family(id, env.metadata());
      try {
        const data = await api.dashboard(id, kind === "aer");
        if (active()) env.render[kind](data);
      } catch (error) {
        if (active() && target)
          view.failure(target, error, () => controller.load(env));
      }
    },
    serverError: view.serverError,
  };
  return controller;
}
