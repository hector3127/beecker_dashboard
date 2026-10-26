// Explicit contract for special account/no-project callbacks during transition.
// Report data belongs to the store; loaders/renderers remain transitional.
export function createProjectCompatibility(documentRoot = document) {
  return {
    reports(state, previous) {
      return this.bindings({
        ...previous,
        account() {
          const value = String(
            documentRoot.getElementById("f-cliente")?.value || "",
          ).trim();
          return !value || /^todos los clientes$/i.test(value) ? "" : value;
        },
        aer: () => state.reportAer,
        ixs: () => state.reportIxs,
      });
    },
    bindings(previous) {
      return {
        previousStart: previous.start,
        previousLoad: previous.load,
        clientChanged() {
          const project = documentRoot.getElementById("f-proyecto");
          if (previous.account() && project)
            project.value = "Todos los proyectos";
          previous.refresh();
          if (previous.account()) return;
          const aer = previous.aer();
          if (aer) previous.renderAer(aer);
          const ixs = previous.ixs();
          if (ixs) previous.renderIxs(ixs);
          previous.risks();
        },
        executive: previous.executive,
      };
    },
  };
}
