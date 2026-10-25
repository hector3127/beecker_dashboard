import * as ai from "./ixs_ai_model.js";
import { milestones } from "./ixs_executive_model.js";

export function createIxsAdapters(store, services) {
  const context = () =>
    ai.context(store.ixsAi, store.ixs, milestones(store.ixs || {}));
  const snapshot = () => ai.snapshot(store.ixsAi, context());
  return {
    context,
    snapshot,
    changes: () => ai.changes(store.ixsAi, snapshot),
    capacity: () => ai.capacity(store.ixsAi),
    support(reload) {
      return {
        project: () => store.ixs,
        tab: () => store.ixsTab,
        selectMilestones(project) {
          store.projectId = project.proyecto.id;
          store.milestones = project.hitosAdicionales || [];
        },
        edit: (tipo, indice, fechaISO, observacion) =>
          services.milestones.edit(store.projectId, store.milestones, reload, {
            tipo,
            indice,
            fechaISO,
            observacion,
          }),
      };
    },
    load(source, paint) {
      return services.sources[source](store.ixsAi, {
        current: services.current,
        paint,
      });
    },
    actions(callbacks) {
      return services.controller.actions(store.ixsAi, {
        current: services.current,
        paint: callbacks.paint,
        context,
        snapshot,
        tab: callbacks.tab,
        loadDrive: callbacks.loadDrive,
        raid: (type, text) => {
          callbacks.raidOpen(type);
          const input = document.getElementById("ixs-raid-free");
          if (input) input.value = text;
          callbacks.raidManual();
        },
      });
    },
  };
}
