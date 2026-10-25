// Contracts for shared Actions, AER Risks/AI and IXS AI validity.
// UI/transport callbacks stay injectable while compatibility is retired.
export function createProjectFeatureContexts(store) {
  const base = (tab) => {
    const snapshot = store.aer;
    return {
      id: snapshot.proyecto.id,
      dashboard: snapshot,
      current: () => store.aer === snapshot,
      active: () => store.aerTab === tab,
    };
  };
  return {
    risks: (callbacks) => ({ ...base("riesgos"), ...callbacks }),
    actions(callbacks) {
      const snapshot = store.aer,
        id = snapshot.proyecto.id;
      const family =
        ["cliente", "acciones"].includes(store.ixsTab) &&
        !!document.querySelector("#dashboard-proyecto-detalle .ixs-shell")
          ? "ixs"
          : "aer";
      const active = () =>
        family === "ixs"
          ? store.ixsTab === "acciones"
          : store.aerTab === "acciones";
      return {
        id,
        family,
        dashboard: snapshot,
        current: () => store.aer === snapshot,
        active,
        ...callbacks,
        actions: (rows) => {
          snapshot.acciones = rows;
          if (active()) callbacks.paint();
        },
        storeActions: (rows) => {
          snapshot.acciones = rows;
        },
        parts: () => store.aerAi.accionesPartes,
        partsLoading: () => store.aerAi.cargandoPartes,
        loadingParts: (flag) => {
          store.aerAi.cargandoPartes = flag;
        },
        setParts: (rows) => {
          store.aerAi.accionesPartes = rows;
          if (family === "ixs" && store.clientCache[id])
            store.clientCache[id].partes = rows;
        },
        paintParts: () => {
          if (active() || (family === "aer" && store.aerTab === "ia"))
            callbacks.paint();
        },
      };
    },
    aerSources(callbacks) {
      const snapshot = store.aer,
        state = store.aerAi;
      return {
        id: snapshot.proyecto.id,
        state,
        current: () =>
          store.aer &&
          store.aer.proyecto.id === snapshot.proyecto.id &&
          store.aerAi === state,
        active: () => store.aerTab === "ia",
        ...callbacks,
      };
    },
    aerPresentation(callbacks) {
      const state = store.aerAi,
        id = store.aer.proyecto.id;
      return {
        dashboard: store.aer,
        state,
        current: () => store.aerAi === state && store.aer.proyecto.id === id,
        active: () => store.aerTab === "ia",
        ...callbacks,
      };
    },
    aerActions(callbacks) {
      const state = store.aerAi,
        id = store.aer.proyecto.id;
      return {
        id,
        state,
        current: () => store.aerAi === state && store.aer?.proyecto.id === id,
        active: () => store.aerTab === "ia",
        ...callbacks,
      };
    },
    ixsCurrent: (state) =>
      store.ixsAi === state && store.ixs?.proyecto.id === state.id,
  };
}
