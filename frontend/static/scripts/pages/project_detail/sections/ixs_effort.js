import { renderEffort, effortResources } from "./ixs_effort_view.js";
import {
  renderClockify,
  activityModal,
  recordsModal,
} from "./ixs_effort_clockify.js";
import { excessDialog, renderExcess, excessCsv } from "./ixs_effort_excess.js";
import {
  currentWeek,
  activityRows,
  excessByPerson,
} from "./ixs_effort_model.js";
import { renderTasks } from "./ixs_executive_view.js";

export { effortResources };

/** One project cache, exactly as the previous ixsClockifyState. */
export function createEffortController(api) {
  let state = {
      proyectoId: "",
      registros: null,
      cargando: false,
      error: "",
      requestId: 0,
    },
    target,
    data,
    lifecycle;
  let pages = {},
    sorts = {};
  const close = (id) => document.getElementById(id)?.remove();
  const value = (id) => document.getElementById(id)?.value || "";
  const filtered = () =>
    (state.registros || []).filter(
      (x) =>
        x.fecha &&
        (!state.desde || x.fecha >= state.desde) &&
        (!state.hasta || x.fecha <= state.hasta),
    );
  const excess = () => {
    const from = value("ixs-excess-from"),
      to = value("ixs-excess-to");
    return excessByPerson(data?.filasRecursosCompleto, state.registros)
      .map((p) => ({
        ...p,
        records: p.records.filter(
          (x) => (!from || x.fecha >= from) && (!to || x.fecha <= to),
        ),
      }))
      .filter((p) => p.records.length);
  };
  const paintExcess = () => {
    if (!document.getElementById("ixs-excess-records")) return;
    renderExcess(
      state,
      state.cargando || state.error ? [] : excess(),
      pages,
      sorts,
      {
        page: (person, page) => {
          pages[person] = page;
          paintExcess();
        },
        sort: (person, field) => {
          const old = sorts[person];
          sorts[person] = {
            field,
            dir: old && old.field === field ? -old.dir : 1,
          };
          pages[person] = 1;
          paintExcess();
        },
      },
    );
  };
  function filterExcess() {
    const from = value("ixs-excess-from"),
      to = value("ixs-excess-to");
    if (from && to && from > to) {
      alert("La fecha de inicio debe ser anterior o igual a la fecha de fin.");
      return false;
    }
    pages = {};
    paintExcess();
    return true;
  }
  function exportExcess() {
    if (!filterExcess()) return;
    const people = excess();
    if (!people.length) return;
    const blob = new Blob([excessCsv(data.proyecto.id, people)], {
        type: "text/csv;charset=utf-8;",
      }),
      url = URL.createObjectURL(blob),
      link = document.createElement("a");
    link.href = url;
    link.download =
      String(data.proyecto.id).replace(/[^a-z0-9_.-]/gi, "_") +
      "_horas_excedidas_" +
      value("ixs-excess-from") +
      "_" +
      value("ixs-excess-to") +
      ".csv";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const actions = {
    activity: (i, j) => {
      const task = activityRows(state.registros || [])[Number(i)],
        person = task?.personas[Number(j)];
      if (task && person)
        activityModal(task, person, () => close("ixs-actividad-modal"));
    },
    records: () =>
      recordsModal(state, filtered(), () => close("ixs-clockify-modal")),
    filter: () => {
      const desde = value("ixs-clock-desde"),
        hasta = value("ixs-clock-hasta");
      if (!desde || !hasta || desde > hasta) {
        alert(
          "Selecciona fechas válidas; Desde debe ser anterior o igual a Hasta.",
        );
        return;
      }
      state.desde = desde;
      state.hasta = hasta;
      paint();
    },
    excess: () => {
      pages = {};
      sorts = {};
      excessDialog(state.registros, {
        filter: filterExcess,
        export: exportExcess,
        close: () => close("ixs-excess-modal"),
      });
      paintExcess();
      if (!Array.isArray(state.registros)) load();
    },
  };
  function paint() {
    paintExcess();
    if (target?.isConnected && lifecycle.current(data) && lifecycle.active())
      renderClockify(target, state, filtered(), actions);
  }
  function load() {
    if (state.cargando || Array.isArray(state.registros)) {
      paint();
      return;
    }
    const st = state,
      id = st.proyectoId,
      token = ++st.requestId;
    st.cargando = true;
    st.error = "";
    paint();
    const current = () =>
      state === st && st.proyectoId === id && st.requestId === token;
    api
      .records(id)
      .then((result) => {
        if (!current()) return;
        st.cargando = false;
        if (!result || !result.ok) {
          st.registros = [];
          st.error =
            result?.error ||
            "No fue posible obtener los registros de Clockify.";
        } else {
          st.registros = Array.isArray(result.registros)
            ? result.registros
            : [];
          st.error = "";
        }
        paint();
      })
      .catch((error) => {
        if (!current()) return;
        st.cargando = false;
        st.error = error?.message || String(error);
        st.registros = [];
        paint();
      });
  }
  return {
    selectProject(project) {
      data = project;
      if (state.proyectoId !== project.proyecto.id)
        state = {
          proyectoId: project.proyecto.id,
          registros: null,
          cargando: false,
          error: "",
          ...currentWeek(),
          requestId: 0,
        };
    },
    mount(node, project, guards) {
      target = node;
      data = project;
      lifecycle = guards;
      const id = project.proyecto.id;
      if (state.proyectoId !== id)
        state = {
          proyectoId: id,
          registros: null,
          cargando: false,
          error: "",
          ...currentWeek(),
          requestId: 0,
        };
      renderEffort(node, project);
      const tasks = node.querySelector("#ixs-tasks-effort");
      const active = () =>
        node.isConnected && guards.current(project) && guards.active();
      api
        .tasks(id)
        .then((result) => {
          if (active()) renderTasks(tasks, result);
        })
        .catch((error) => {
          if (active())
            tasks.textContent = "Error Clockify: " + (error?.message || error);
        });
      load();
    },
    updateResources(node, project) {
      node.replaceChildren(effortResources(project.filasRecursosCompleto));
    },
  };
}
