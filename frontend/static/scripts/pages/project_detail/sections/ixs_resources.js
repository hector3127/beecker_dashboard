import { renderResources, resourceEditor } from "./ixs_resources_view.js";

export function createResourcesController(api) {
  const state = {
    proyectoId: "",
    filas: [],
    registros: [],
    cargando: false,
    error: "",
    saving: false,
    requestId: 0,
  };
  let target, data, guards;
  const close = () => document.getElementById("ixs-recurso-modal")?.remove();
  const paint = () => {
    if (
      target?.isConnected &&
      guards.current(data) &&
      guards.active() &&
      data.proyecto.id === state.proyectoId
    )
      renderResources(target, data, state, edit);
  };
  function edit(name = "") {
    const project = data;
    resourceEditor(project, state, name, {
      close,
      save: (event) => save(event, project),
    });
  }
  async function save(event, project) {
    event.preventDefault();
    if (state.saving) return;
    const form = event.target,
      button = form.querySelector('[type="submit"]'),
      fields = form.elements;
    const payload = {
      idProyecto: state.proyectoId,
      nombre: fields.nombre.value,
      rol: fields.rol.value,
      horasEstimadas: fields.horas.value,
      activo: fields.activo.value === "true",
    };
    state.saving = true;
    button.disabled = true;
    button.textContent = "Guardando…";
    const current = () =>
      guards.current(project) &&
      data === project &&
      project.proyecto.id === state.proyectoId;
    const error = (text) => {
      if (current() && form.isConnected)
        form.querySelector("#ixs-recurso-error").textContent = text;
    };
    try {
      const result = await api.saveResource(project.proyecto.id, payload);
      if (!current()) return;
      if (!result || !result.ok) {
        error(result?.error || "No se pudo guardar.");
        return;
      }
      if (result.proyectoId !== state.proyectoId) return;
      state.filas = result.filas || [];
      project._resourceStatesLoaded = false;
      close();
      paint();
    } catch (e) {
      error(e?.message || String(e));
    } finally {
      state.saving = false;
      button.disabled = false;
      button.textContent = "Guardar recurso";
    }
  }
  async function load() {
    const id = state.proyectoId,
      token = ++state.requestId;
    state.cargando = true;
    state.error = "";
    state.registros = [];
    paint();
    const current = () => state.requestId === token && state.proyectoId === id;
    try {
      const assigned = await api.resources(id);
      if (!current()) return;
      if (!assigned || !assigned.ok) {
        state.error =
          assigned?.error || "No se pudieron consultar las asignaciones.";
        state.cargando = false;
        paint();
        return;
      }
      state.filas = assigned.filas || [];
      paint();
      try {
        const clocks = await api.records(id);
        if (!current()) return;
        state.registros =
          clocks && clocks.ok && Array.isArray(clocks.registros)
            ? clocks.registros
            : [];
        if (!clocks || !clocks.ok)
          state.error =
            "Clockify: " +
            (clocks?.error || "No se pudieron consultar las horas.");
      } catch (e) {
        if (!current()) return;
        state.error = "Clockify: " + (e?.message || e);
      }
      state.cargando = false;
      paint();
    } catch (e) {
      if (!current()) return;
      state.error = e?.message || String(e);
      state.cargando = false;
      paint();
    }
  }
  return {
    mount(node, project, lifecycle) {
      target = node;
      data = project;
      guards = lifecycle;
      state.proyectoId = project.proyecto.id;
      load();
    },
  };
}
