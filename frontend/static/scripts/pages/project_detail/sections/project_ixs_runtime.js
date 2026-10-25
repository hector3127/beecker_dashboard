// Direct IXS navigation/rendering/editors/RAID. Previous view and reload still
// come from compatibility; styles are already linked by the modern template.
export function createIxsRuntime(store, services) {
  let callbacks;
  const aiCallbacks = () => ({
    paint: () => runtime.paintAi(),
    tab: (tab) => runtime.select(tab),
    loadDrive: () => services.adapters.load("drive", () => runtime.paintAi()),
    raidOpen: (type) => services.tools.openRaid(type),
    raidManual: () => services.tools.manualRaid(),
  });
  const session = () =>
    services.contexts.session({
      styles: services.tools.styles,
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
          createRaid: (type) => services.tools.openRaid(type),
          previous: callbacks.previous,
          editPlanning: (...args) => services.tools.editPlanning(...args),
          editMarker: (index) =>
            services.support.editMilestone(
              index,
              services.adapters.support(callbacks.reload),
            ),
          extension: () => services.tools.communique(),
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
