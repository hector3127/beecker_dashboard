import { renderPlanning } from "./ixs_planning_view.js";
import { planningAzureSection } from "./ixs_planning_azure.js";
import { createWorkItemActions } from "./ixs_work_item_actions.js";

export function createPlanningController(api) {
  let target, project, plan, azure, lifecycle;
  const workItems = createWorkItemActions(api);
  let workItemActions;
  function paint() {
    if (
      !target?.isConnected ||
      !lifecycle.current(project) ||
      !lifecycle.active() ||
      project.proyecto.id !== plan.proyectoId
    )
      return;
    renderPlanning(target, project, plan, azure, {
      ...lifecycle.actions,
      azureSection: (state) => planningAzureSection(state, workItemActions),
    });
  }
  async function loadAzure(owner, state, guards) {
    const id = owner.proyecto.id,
      token = ++state.requestId;
    state.proyectoId = id;
    state.items = [];
    state.allItems = [];
    state.cargando = true;
    state.error = "";
    const current = () =>
      guards.current(owner) &&
      state.requestId === token &&
      state.proyectoId === id;
    try {
      const result = await api.planningAzure(id);
      if (!current() || !guards.active()) return;
      state.cargando = false;
      if (!result || !result.ok)
        state.error =
          result?.error || "No se pudieron consultar los Work Items.";
      else {
        state.items = Array.isArray(result.items) ? result.items : [];
        state.allItems = Array.isArray(result.allItems)
          ? result.allItems
          : state.items;
        state.error = "";
      }
      guards.syncAzure(id, state.items);
      paint();
    } catch (error) {
      if (!current()) return;
      state.cargando = false;
      state.error = error?.message || String(error);
      guards.syncAzure(id, []);
      paint();
    }
  }
  async function loadPlan(owner, state, guards, token) {
    const id = owner.proyecto.id,
      current = () =>
        guards.current(owner) &&
        state.requestId === token &&
        state.proyectoId === id;
    try {
      const result = await api.planning(id);
      if (!current()) return;
      state.cargando = false;
      if (!result || !result.ok)
        state.error = result?.error || "No se pudo cargar la planeación.";
      else {
        state.vacaciones = result.vacaciones || [];
        state.compromisos = result.compromisos || [];
      }
      paint();
    } catch (error) {
      if (!current()) return;
      state.cargando = false;
      state.error = error?.message || String(error);
      paint();
    }
  }
  return {
    paint,
    mount(node, data, planState, azureState, guards) {
      target = node;
      project = data;
      plan = planState;
      azure = azureState;
      lifecycle = guards;
      workItemActions = workItems.bind(data, azureState, guards, paint);
      const id = data.proyecto.id,
        token = ++plan.requestId;
      if (plan.proyectoId !== id) {
        plan.vacaciones = [];
        plan.compromisos = [];
      }
      plan.proyectoId = id;
      plan.cargando = true;
      plan.error = "";
      azure.proyectoId = id;
      azure.items = [];
      azure.allItems = [];
      azure.cargando = true;
      azure.error = "";
      paint();
      guards.resources();
      loadAzure(data, azure, guards);
      loadPlan(data, plan, guards, token);
    },
  };
}
