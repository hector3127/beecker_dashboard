import { el } from "#app/lib/dom.js";
import { genericExecutiveModel } from "./generic_executive_model.js";
import { genericHeader } from "./generic_header_view.js";
import { genericTimelineView } from "./generic_timeline_view.js";
import { resourcePanel, milestonePanel } from "./generic_panels_view.js";

export function createGenericExecutive(store, services) {
  return {
    mount(data) {
      const target = document.getElementById("dashboard-proyecto-detalle");
      if (!target) {
        console.warn(
          "renderDashboardEjecutivoProyecto: vista ya no está en el DOM.",
        );
        return;
      }
      if (!data || !data.proyecto) {
        target.replaceChildren(
          el(
            "div",
            { class: "loading" },
            data?.errorServidor
              ? "Error: " + data.errorServidor
              : "No se pudo cargar el dashboard ejecutivo.",
          ),
        );
        return;
      }
      const model = genericExecutiveModel(data, store.metadata);
      store.milestones = model.milestones;
      store.projectId = data.proyecto.id;
      Object.assign(data.proyecto, model.projectPatch);
      services.layout(target, store.projectId, store.milestones);
      const replace = (id, ...nodes) =>
        target.querySelector("#" + id)?.replaceWith(...nodes);
      const header = genericHeader(data, model.context);
      replace("generic-header-placeholder", header.header);
      replace("generic-kpis-placeholder", header.kpis);
      replace("generic-resources-panel", resourcePanel(data));
      replace("generic-milestones-panel", milestonePanel(model.summary));
      replace(
        "generic-project-timeline",
        genericTimelineView(model.timeline, model.now),
      );
      services.charts.mount(data);
      services.range.load(store.projectId, "rango-clockify-dashboard");
      services.sources.raid(store.projectId);
      services.sources.tasks(store.projectId);
    },
  };
}
