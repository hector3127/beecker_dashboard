import { createAzureController } from "./ixs_azure.js";
import { azureTabView } from "./ixs_azure_tab_view.js";
import { renderSummary } from "./ixs_azure_summary.js";
import { planningAzureSection } from "./ixs_planning_azure.js";
import { createWorkItemActions } from "./ixs_work_item_actions.js";

export function createAzureTab(api, groups) {
  const loader = createAzureController(api),
    writes = createWorkItemActions(api);
  return {
    mount(root, project, sharedState, guards) {
      const state = { ...sharedState },
        tableState = { items: sharedState.items || [], error: "", cargando: false };
      const actions = writes.bind(project, tableState, guards, () => {}, {
        refreshDeadline: false,
      });
      const table = planningAzureSection(tableState, actions, "azure");
      const load = (force) =>
        loader.load(root, project, state, force, {
          ...guards,
          loaded: (result) => {
            Object.assign(state, result);
            tableState.items = result.items;
            guards.sync(state);
            renderSummary(root, state);
            table.refreshAzure();
            groups.render(state);
          },
        });
      root.dataset.renderer = "modular-azure";
      root.replaceChildren(...azureTabView(table, () => load(true)));
      load(false);
    },
  };
}
