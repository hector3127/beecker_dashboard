import { renderShell, loading, invalidRefresh } from "./project_shell_view.js";

export function createProjectShell(api) {
  const requests = { aer: 0, ixs: 0 };
  const bind = (env) => {
    const actions = {
      select(tab) {
        env.tab(env.family === "aer" && tab === "minutas" ? "ia" : tab);
        env.render();
        if (env.family === "aer") {
          if (env.tab() === "ia") {
            env.loads.analysis();
            env.loads.minutes();
            env.loads.config();
            env.loads.summary();
            env.loads.parts();
          } else if (env.tab() === "acciones") env.loads.parts();
        }
      },
      async refresh() {
        const family = env.family,
          id = env.project.proyecto?.id;
        if (!id) return;
        const tab = env.tab(),
          token = ++requests[family],
          target = document.getElementById(
            family === "aer" ? "aer-tab-content" : "ixs-tab-contenido",
          );
        const current = () => requests[family] === token && env.current();
        loading(target, family);
        try {
          const result = await api.dashboard(id, family === "aer");
          if (!current()) return;
          if (
            family === "aer"
              ? !result?.ok
              : !result?.proyecto || result.proyecto.id !== id
          ) {
            if (family === "aer")
              env.error(result?.error || "Error actualizando");
            else invalidRefresh(target);
            return;
          }
          env.apply(result, tab);
        } catch (error) {
          if (!current()) return;
          if (family === "aer") env.error(error);
          else {
            const root = document.getElementById("ixs-tab-contenido");
            if (root)
              root.textContent =
                "Error actualizando: " + (error?.message || error);
          }
        }
      },
    };
    return actions;
  };
  return {
    bind,
    mount(target, env) {
      renderShell(target, env, bind(env));
      env.dispatch();
    },
  };
}
