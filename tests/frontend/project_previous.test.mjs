import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs
  .readFileSync(
    "frontend/static/scripts/pages/project_detail/sections/project_previous.js",
    "utf8",
  )
  .replace(/import[^;]+;/g, "")
  .replace("export function", "function");
function setup(project) {
  const store = { ixs: project, ixsTab: "unknown" },
    calls = [],
    nodes = [];
  const context = {
    document: { getElementById: () => ({ prepend: (n) => nodes.push(n) }) },
    el: (tag, props, ...children) => ({ tag, props, children }),
  };
  vm.runInNewContext(source, context);
  return {
    store,
    calls,
    nodes,
    controller: context.createProjectPrevious(store, {
      executive: { mount: (data) => calls.push(["generic", data]) },
      mountIxs: () => calls.push(["ixs"]),
    }),
  };
}

test("missing project does not mount or add a return control", () => {
  for (const project of [null, {}]) {
    const s = setup(project);
    s.controller.open();
    assert.deepEqual(s.calls, []);
    assert.deepEqual(s.nodes, []);
  }
});

test("previous view uses exact project object and return selects executive without reload", () => {
  const project = { proyecto: { id: "P'\"><img>" } },
    s = setup(project);
  s.controller.open();
  assert.equal(s.calls[0][1], project);
  assert.equal(s.nodes[0].props.class, "ixs-shell project-previous-return");
  const button = s.nodes[0].children[0];
  button.props.onclick();
  assert.equal(s.store.ixsTab, "resumen");
  assert.deepEqual(s.calls[1], ["ixs"]);
  assert.equal(button.children[0], "← Volver al nuevo ejecutivo");
});

test("old return button cannot change another project's tab", () => {
  const s = setup({ proyecto: { id: "A" } });
  s.controller.open();
  const back = s.nodes[0].children[0].props.onclick;
  s.store.ixs = { proyecto: { id: "B" } };
  back();
  assert.equal(s.store.ixsTab, "unknown");
  assert.equal(s.calls.length, 1);
  s.store.ixs = null;
  back();
  assert.equal(s.calls.length, 1);
});
