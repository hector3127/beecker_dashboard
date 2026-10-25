// AER coordination through modular state/contracts/controllers, including the
// AER presentation shared by IXS Client/Actions. No legacy callbacks are needed.
export function createAerRuntime(store, services) {
  const common = () => ({
    paint: () => runtime.dispatch(),
    error: services.entry.serverError,
  });
  const data = () =>
    services.views.beeAerAiModel.context(store.aer, store.aerAi);
  const shell = () =>
    services.contexts.shell("aer", {
      render: () => runtime.mount(),
      dispatch: () => runtime.dispatch(),
      error: services.entry.serverError,
      loads: Object.fromEntries(
        ["analysis", "minutes", "config", "summary", "parts"].map((name) => [
          name,
          () => runtime.load(name),
        ]),
      ),
    });
  const runtime = {
    initialize(project) {
      // Modern CSS is already linked by project_detail.html; the old ensure
      // helper was a no-op when that link existed.
      return services.session.aer(
        project,
        services.contexts.session({
          styles: { aer() {} },
          render: { aer: () => runtime.mount() },
        }),
      );
    },
    mount() {
      const target = document.getElementById("dashboard-proyecto-detalle");
      if (target && store.aer) return services.shell.mount(target, shell());
    },
    dispatch() {
      return services.tabs.aer(runtime.tabs());
    },
    tabs() {
      return services.contexts.tabs({
        selectAer: (tab) => runtime.select(tab),
        selectIxs: services.selectIxs,
        aerContexts: {
          planning: () => runtime.planningContext(),
          effort: () => runtime.effortContext(),
          resources: () => runtime.resourcesContext(),
          risks: () => runtime.risksContext(),
          actions: () => runtime.actionsContext(),
          ai: () => runtime.aiPresentationContext(),
        },
      });
    },
    select(tab) {
      if (store.aer) return services.shell.bind(shell()).select(tab);
    },
    refresh() {
      if (store.aer) return services.shell.bind(shell()).refresh();
    },
    planningContext() {
      return services.panels.planning({
        ...common(),
        saving: services.feedback.saving,
        reload: () => runtime.refresh(),
        communique: () => runtime.communique(),
      });
    },
    effortContext() {
      return services.panels.effort(common());
    },
    resourcesContext() {
      return services.panels.resources({
        ...common(),
        saving: services.feedback.saving,
      });
    },
    risksContext() {
      return services.features.risks({
        ...common(),
        saving: services.feedback.saving,
        openAction: () => runtime.actions().open(),
      });
    },
    actionsContext() {
      return services.features.actions({
        ...common(),
        toast: services.feedback.toast,
      });
    },
    actions() {
      return services.views.beeProjectActions.bind(runtime.actionsContext());
    },
    risks() {
      return services.views.beeAerRisks.bind(runtime.risksContext());
    },
    sources() {
      return services.views.beeAerAiSources.bind(
        services.features.aerSources({
          paint: () => runtime.dispatch(),
          context: data,
          toast: services.feedback.toast,
          openConfig: () => runtime.presentation().config(),
        }),
      );
    },
    load(name, argument) {
      return name === "parts"
        ? runtime.actions().loadParts(argument)
        : runtime.sources()[name](argument);
    },
    aiData: data,
    aiPresentationContext() {
      return services.features.aerPresentation({
        paint: () => runtime.dispatch(),
        toast: services.feedback.toast,
        actions: {
          analyze: (force) => runtime.aiActions().analyze(force),
          generateSummary: () => runtime.aiActions().generateSummary(),
          generateMail: () => runtime.aiActions().generateMail(),
          generateMinute: () => runtime.aiActions().generateMinute(),
          saveMinute: () => runtime.aiActions().saveMinute(),
          copyMinute: () => runtime.aiActions().copyMinute(),
          copySavedMinute: () => runtime.aiActions().copySavedMinute(),
          copySummary: () => runtime.aiActions().copySummary(),
          saveConfig: (search) => runtime.aiActions().saveConfig(search),
          resetPrompt: () => runtime.aiActions().resetPrompt(),
          loadConfig: (open) => runtime.load("config", open),
          files: () => runtime.load("files"),
          tab: (tab) => runtime.select(tab),
          ask: () => runtime.aiActions().ask(),
          action: () => runtime.actions().open(),
          risk: () => runtime.risks().open(),
        },
      });
    },
    presentation() {
      return services.views.beeAerAiPresentation.bind(
        runtime.aiPresentationContext(),
      );
    },
    aiActions() {
      return services.views.beeAerAiActions.bind(
        services.features.aerActions({
          ...common(),
          toast: services.feedback.toast,
          context: data,
          presentation: () => runtime.presentation(),
          sources: () => runtime.sources(),
          tab: () => runtime.select("ia"),
        }),
      );
    },
    communique() {
      const project = store.aer?.proyecto || {};
      if (services.views.beeProjectCommunique && project.id)
        return services.views.beeProjectCommunique.open({
          projectId: project.id,
          projectName: project.nombre || "",
          family: "aer",
        });
    },
  };
  return runtime;
}
