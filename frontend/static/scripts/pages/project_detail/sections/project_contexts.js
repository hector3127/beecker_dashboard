// State/lifecycle contracts shared by the entry, session, shell and tab registry.
// Compatibility callbacks are supplied by their existing entry points for now.
export function createProjectContexts(store) {
  const cell =
    (key) =>
    (...args) =>
      args.length ? (store[key] = args[0]) : store[key];
  return {
    entry(callbacks) {
      return {
        ...callbacks,
        metadata: cell("metadata"),
        invalidatePrevious: () => {
          ++store.request;
        },
      };
    },
    session(callbacks) {
      return {
        ...callbacks,
        aer: cell("aer"),
        ixs: cell("ixs"),
        aerAi: cell("aerAi"),
        ixsAi: cell("ixsAi"),
        clockify: cell("clockify"),
        aerTab: cell("aerTab"),
        ixsTab: cell("ixsTab"),
        globalId: (id) => {
          store.projectId = id;
        },
        cache: store.clientCache,
      };
    },
    shell(family, callbacks) {
      const aer = family === "aer",
        key = aer ? "aer" : "ixs",
        snapshot = store[key];
      return {
        family,
        project: snapshot,
        metadata: aer ? {} : store.metadata,
        tab: cell(aer ? "aerTab" : "ixsTab"),
        current: () =>
          store[key] === snapshot &&
          !!document.querySelector(
            "#dashboard-proyecto-detalle ." + (aer ? "aer-shell" : "ixs-shell"),
          ),
        render: callbacks.render,
        dispatch: callbacks.dispatch,
        error: callbacks.error,
        loads: callbacks.loads,
        apply(result, tab) {
          if (aer) {
            store.aer = result;
            store.aerTab = tab;
            callbacks.render();
          } else {
            delete store.clientCache[snapshot.proyecto.id];
            callbacks.initializeIxs(result);
          }
        },
      };
    },
    tabs(callbacks) {
      return {
        aer: () => store.aer,
        ixs: () => store.ixs,
        aerTab: cell("aerTab"),
        ixsTab: () => store.ixsTab,
        selectAer: callbacks.selectAer,
        selectIxs: callbacks.selectIxs,
        aerContexts: callbacks.aerContexts,
        ixsStates: () => ({
          planning: store.ixsPlanning,
          planningAzure: store.ixsPlanningAzure,
          azure: store.ixsAzure,
        }),
        resources: callbacks.resources,
        openAi: callbacks.openAi,
        loadClientActions: callbacks.loadClientActions,
        syncPlanningAzure: (id, items) => {
          store.ixsAzure.projectId = id;
          store.ixsAzure.items = items;
        },
        syncAzure: (state) => {
          store.ixsAzure = state;
        },
        createRaid: callbacks.createRaid,
        previous: callbacks.previous,
        planningActions: {
          edit: (type, uid = "", initial) =>
            callbacks.editPlanning(
              type,
              encodeURIComponent(uid).replace(/'/g, "%27"),
              initial,
            ),
          editMarker: callbacks.editMarker,
          extension: callbacks.extension,
          azure: () => callbacks.selectIxs("azure"),
        },
      };
    },
  };
}
