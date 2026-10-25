import test from "node:test";
import assert from "node:assert/strict";
import { createIxsTools } from "../../frontend/static/scripts/pages/project_detail/sections/project_ixs_tools.js";
import { createProjectState } from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";

function setup() {
  const store = createProjectState(),
    calls = [];
  store.ixs = { proyecto: { id: "P", nombre: "Proyecto abierto" } };
  store.ixsPlanning.proyectoId = "P";
  const dates = { stage: "Development", closes: { Development: "2026-10-30" } };
  const tools = createIxsTools(
    store,
    {
      beeIxsPlanningEditor: { open: (...args) => calls.push(args) },
      beeIxsPlanning: { paint: () => calls.push("paint") },
      beeProjectCommunique: { open: (data) => calls.push(data) },
      beeIxsRaidCreator: {
        open: (...args) => calls.push(args),
        manual: () => calls.push("manual"),
      },
      beeIxsRaid: { reload: (force) => calls.push(["reload", force]) },
    },
    {
      suggestedDates: (project) => {
        assert.equal(project, store.ixs);
        return dates;
      },
    },
  );
  return { store, tools, calls, dates };
}

test("planning keeps decoded UID, initial type, shared state and original lifecycle", () => {
  const { store, tools, calls } = setup();
  tools.editPlanning("compromiso", "hito%2F%271", "Hito");
  const [type, uid, initial, state, lifecycle] = calls[0];
  assert.deepEqual([type, uid, initial], ["compromiso", "hito/'1", "Hito"]);
  assert.equal(state, store.ixsPlanning);
  assert.equal(lifecycle.current(), true);
  const result = { vacaciones: [{ uid: "v" }], compromisos: [{ uid: "h" }] };
  lifecycle.saved(result);
  assert.equal(state.vacaciones, result.vacaciones);
  assert.equal(state.compromisos, result.compromisos);
  assert.equal(calls.at(-1), "paint");
  store.ixs = { ...store.ixs };
  assert.equal(lifecycle.current(), false);
});

test("empty UID and missing saved lists keep the previous defaults", () => {
  const { tools, calls } = setup();
  tools.editPlanning("vacacion");
  assert.equal(calls[0][1], "");
  const state = calls[0][3];
  calls[0][4].saved({});
  assert.deepEqual([state.vacaciones, state.compromisos], [[], []]);
});

test("RAID keeps project-ID validity and refreshes the existing registry after creation", () => {
  const { store, tools, calls } = setup();
  const project = store.ixs;
  tools.openRaid("Issue");
  const [type, data, hooks] = calls[0];
  assert.equal(type, "Issue");
  assert.equal(data, project);
  assert.equal(hooks.current(), true);
  store.ixs = { ...project };
  assert.equal(hooks.current(), true);
  store.ixs = { proyecto: { id: "OTHER" } };
  assert.equal(hooks.current(), false);
  hooks.created();
  assert.deepEqual(calls.at(-1), ["reload", true]);
  tools.manualRaid();
  assert.equal(calls.at(-1), "manual");
});

test("Comunicados uses planning ID, project name and the existing suggested dates", () => {
  const { store, tools, calls, dates } = setup();
  store.ixsPlanning.proyectoId = "planning-ID";
  tools.communique();
  assert.deepEqual(calls[0], {
    projectId: "planning-ID",
    projectName: "Proyecto abierto",
    family: "ixb",
    auto: dates,
  });
  store.ixs = null;
  store.ixsPlanning.proyectoId = "";
  tools.communique();
  assert.deepEqual(calls[1], {
    projectId: "",
    projectName: "",
    family: "ixb",
    auto: null,
  });
  tools.styles.aer();
  tools.styles.ixs();
  tools.styles.ai();
});
