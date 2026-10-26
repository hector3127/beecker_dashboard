// Explicit contract for special account/no-project callbacks during transition.
// Providers still supply old reports and caches; ordering and guards stay intact.
export function createProjectCompatibility(documentRoot = document) {
  return {
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
