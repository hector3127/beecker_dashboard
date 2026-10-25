// Direct IXS navigation/rendering. Remaining editor/AER callbacks are supplied
// by the compatibility entry; the runtime itself does not call old renderers.
export function createIxsRuntime(store, services) {
  let callbacks;
  const aiCallbacks = () => ({
    paint: () => runtime.paintAi(),
    tab: (tab) => runtime.select(tab),
    loadDrive: () => services.adapters.load("drive", () => runtime.paintAi()),
    raidOpen: callbacks.createRaid,
    raidManual: callbacks.manualRaid,
  });
  const session = () =>
    services.contexts.session({
      styles: callbacks.styles,
      render: {
        ixs: () => runtime.mount(),
        ai: () => runtime.paintAi(),
        aerTab: () => services.tabs.aer(callbacks.aerTabs()),
      },
      aiLoads: Object.fromEntries(
        ["sources", "history", "drive"].map((source) => [
          source,
          () => services.adapters.load(source, () => runtime.paintAi()),
        ]),
      ),
    });
  const shell = () =>
    services.contexts.shell("ixs", {
      render: () => runtime.mount(),
      dispatch: () => runtime.dispatch(),
      error: services.entry.serverError,
      loads: {},
      initializeIxs: (data) => runtime.initialize(data),
    });
  const runtime = {
    connect(value) {
      callbacks = value;
      return runtime;
    },
    initialize(data) {
      return services.session.ixs(data, session());
    },
    mount() {
      const target = document.getElementById("dashboard-proyecto-detalle");
      if (!target || !store.ixs) return;
      return services.shell.mount(target, shell());
    },
    dispatch() {
      const aer = callbacks.aerTabs();
      return services.tabs.ixs(
        services.contexts.tabs({
          selectAer: aer.selectAer,
          selectIxs: (tab) => runtime.select(tab),
          aerContexts: aer.aerContexts,
          resources: () =>
            services.support.resources(
              services.adapters.support(callbacks.reload),
            ),
          openAi: () => runtime.openAi(),
          loadClientActions: () => runtime.loadClientActions(),
          createRaid: callbacks.createRaid,
          previous: callbacks.previous,
          editPlanning: callbacks.editPlanning,
          editMarker: (index) =>
            services.support.editMilestone(
              index,
              services.adapters.support(callbacks.reload),
            ),
          extension: callbacks.extension,
        }),
      );
    },
    select(tab) {
      if (store.ixs) return services.shell.bind(shell()).select(tab);
    },
    refresh() {
      if (store.ixs) return services.shell.bind(shell()).refresh();
    },
    openAi() {
      return services.session.ai(session());
    },
    paintAi() {
      return services.adapters.paint(aiCallbacks());
    },
    aiActions() {
      return services.adapters.actions(aiCallbacks());
    },
    loadClientActions() {
      return services.session.clientActions(session());
    },
  };
  return runtime;
}
