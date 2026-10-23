// Data transport only. The previous IA renderer/actions remain for later blocks.
const errorText = (error) => error?.message || String(error);
export function createAiSources(api) {
  const sources = [
    ["azure", "planningAzure"],
    ["plan", "planning"],
    ["resources", "resources"],
    ["clockify", "records"],
    ["cliente", "client"],
    ["raid", "raidRegistry"],
  ];
  return {
    sources(state, guards) {
      const id = state.id,
        token = ++state.request;
      const current = () =>
        state.id === id && state.request === token && guards.current(state);
      return Promise.all(
        sources.map(async ([key, method]) => {
          try {
            const result = await api[method](id);
            if (!current()) return;
            if (result?.ok) {
              state[key] = result;
              delete state.sourceErrors[key];
            } else
              state.sourceErrors[key] = result?.error || "Fuente no disponible";
          } catch (error) {
            if (!current()) return;
            state.sourceErrors[key] = errorText(error);
          }
          guards.paint();
        }),
      );
    },
    history(state, guards) {
      const id = state.id,
        token = state.request;
      const current = () =>
        state.id === id && state.request === token && guards.current(state);
      return Promise.all(
        [
          ["memoria", "aiMemory"],
          ["minutas", "aiMinutes"],
          ["analisisGuardado", "aiAnalysis"],
        ].map(async ([key, method]) => {
          try {
            const result = await api[method](id);
            if (!current()) return;
            if (result?.ok) {
              if (key === "analisisGuardado") {
                if (result.analisis && !state.analisis && !state.loading)
                  state.analisis = {
                    ok: true,
                    analisis: result.analisis,
                    evidencias: result.evidencias || [],
                    fecha: result.fecha,
                    desdeMemoria: !!result.desdeMemoria,
                  };
              } else state[key] = key === "minutas" ? result.filas : result;
            } else state.sourceErrors[key] = result?.error || "No disponible";
          } catch (error) {
            if (!current()) return;
            state.sourceErrors[key] = errorText(error);
          }
          guards.paint();
        }),
      );
    },
    async drive(state, guards) {
      const id = state.id;
      if (!id || state.driveLoading) return;
      const current = () => state.id === id && guards.current(state);
      state.driveLoading = true;
      state.driveError = "";
      guards.paint();
      try {
        const config = await api.aiDriveFolders(id);
        if (!current()) return;
        state.driveConfig = config?.ok ? config : null;
        if (
          !config?.ok ||
          (!(config.carpetas || []).length &&
            !(config.transcripciones || []).length)
        ) {
          state.driveLoading = false;
          state.driveFiles = [];
          state.driveError = config && !config.ok ? config.error : "";
          guards.paint();
          return;
        }
        const result = await api.aiDriveFiles(id);
        if (!current()) return;
        state.driveLoading = false;
        state.driveFiles = result?.ok ? result.files || [] : [];
        state.driveSelected = (state.driveSelected || []).filter((fid) =>
          state.driveFiles.some(
            (f) => f.id === fid && f.tipo === "transcripciones",
          ),
        );
        state.driveError =
          result && !result.ok
            ? result.error
            : result?.limited
              ? "Se muestran los primeros 250 archivos."
              : "";
      } catch (error) {
        if (!current()) return;
        state.driveLoading = false;
        state.driveError = errorText(error);
      }
      guards.paint();
    },
  };
}
