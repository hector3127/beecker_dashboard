import {
  initialState,
  currentRecords,
  effortModel,
} from "./aer_effort_model.js";
import { renderEffort, openRecords } from "./aer_effort_view.js";

export function createAerEffort(api) {
  let generation = 0;
  const bind = (env) => ({
    initialize() {
      env.setState(initialState(env.state()));
    },
    records() {
      env.setState(initialState(env.state()));
      return currentRecords(env.dashboard, env.state());
    },
    openRecords() {
      env.setState(initialState(env.state()));
      return openRecords(effortModel(env.dashboard, env.state()));
    },
    async query() {
      const state = env.state(),
        desde =
          document.getElementById("aer-clock-desde")?.value || state.desde,
        hasta =
          document.getElementById("aer-clock-hasta")?.value || state.hasta;
      if (!desde || !hasta) {
        alert("Selecciona Desde y Hasta.");
        return;
      }
      if (hasta < desde) {
        alert("Hasta no puede ser menor que Desde.");
        return;
      }
      const request = ++generation;
      env.setState({ ...state, desde, hasta, cargando: true });
      try {
        const result = await api.aerRecords(env.id, desde, hasta);
        if (request !== generation || !env.current()) return;
        env.setState({ ...env.state(), cargando: false });
        if (!result?.ok) {
          env.error(result?.error || "No se pudieron consultar los registros.");
          return;
        }
        env.setState({
          ...env.state(),
          registros: result.registros || [],
          total: Number(result.total || 0),
        });
        if (env.active()) env.paint();
      } catch (error) {
        if (request === generation && env.current()) {
          env.setState({ ...env.state(), cargando: false });
          env.error(error);
        }
      }
    },
  });
  return {
    bind,
    mount(target, env) {
      const actions = bind(env);
      actions.initialize();
      renderEffort(target, effortModel(env.dashboard, env.state()), actions);
    },
  };
}
