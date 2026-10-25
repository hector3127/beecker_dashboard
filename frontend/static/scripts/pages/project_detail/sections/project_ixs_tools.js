// Shared IXS editors use the same state, lifecycle and existing controllers.
export function createIxsTools(store, views, support) {
  return {
    // All three stylesheets are linked by the modern project template.
    styles: { aer() {}, ixs() {}, ai() {} },
    openRaid(type) {
      const project = store.ixs;
      return views.beeIxsRaidCreator.open(type, project, {
        current: () => store.ixs?.proyecto.id === project.proyecto.id,
        created: () => views.beeIxsRaid.reload(true),
      });
    },
    manualRaid() {
      return views.beeIxsRaidCreator.manual();
    },
    editPlanning(type, encoded, initialType) {
      const project = store.ixs,
        state = store.ixsPlanning;
      return views.beeIxsPlanningEditor.open(
        type,
        encoded ? decodeURIComponent(encoded) : "",
        initialType,
        state,
        {
          current: () =>
            store.ixs === project && state.proyectoId === project.proyecto.id,
          saved(result) {
            state.vacaciones = result.vacaciones || [];
            state.compromisos = result.compromisos || [];
            views.beeIxsPlanning.paint();
          },
        },
      );
    },
    communique() {
      const project = store.ixs;
      return views.beeProjectCommunique.open({
        projectId: store.ixsPlanning.proyectoId || "",
        projectName: project?.proyecto?.nombre || "",
        family: "ixb",
        auto: project ? support.suggestedDates(project) : null,
      });
    },
  };
}
