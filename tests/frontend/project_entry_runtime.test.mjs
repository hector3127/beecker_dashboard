import test from "node:test";
import assert from "node:assert/strict";
import { createEntryRuntime } from "../../frontend/static/scripts/pages/project_detail/sections/project_entry_runtime.js";
import { createProjectContexts } from "../../frontend/static/scripts/pages/project_detail/sections/project_contexts.js";
import { createProjectState } from "../../frontend/static/scripts/pages/project_detail/sections/project_state.js";

function setup() {
  const store = createProjectState(),
    calls = [];
  const services = {
    contexts: createProjectContexts(store),
    entry: {
      load: (env) => {
        calls.push(env);
        return "loaded";
      },
    },
    aer: (data) => calls.push(["aer", data]),
    ixs: (data) => calls.push(["ixs", data]),
  };
  const compatibility = Object.fromEntries(
    ["previousStart", "previousLoad", "clientChanged", "executive"].map(
      (name) => [name, (...args) => calls.push([name, ...args])],
    ),
  );
  return {
    store,
    calls,
    compatibility,
    runtime: createEntryRuntime(services).connect(compatibility),
  };
}

test("AER and IXS route directly to runtimes while metadata and sequence use the store", () => {
  const { store, calls, runtime } = setup(),
    env = runtime.context(),
    data = { proyecto: { id: "P" } };
  env.render.aer(data);
  env.render.ixs(data);
  assert.deepEqual(calls, [
    ["aer", data],
    ["ixs", data],
  ]);
  const metadata = { P: { servicio: "IXB" } };
  env.metadata(metadata);
  assert.equal(store.metadata, metadata);
  env.invalidatePrevious();
  assert.equal(store.request, 1);
});

test("generic/client/empty-project fallbacks preserve their callbacks and arguments", () => {
  const { calls, runtime, compatibility } = setup(),
    env = runtime.context();
  assert.equal(env.previousStart, compatibility.previousStart);
  assert.equal(env.previousLoad, compatibility.previousLoad);
  assert.equal(env.clientChanged, compatibility.clientChanged);
  env.previousStart();
  env.previousLoad();
  env.clientChanged();
  env.render.executive("data");
  assert.deepEqual(calls, [
    ["previousStart"],
    ["previousLoad"],
    ["clientChanged"],
    ["executive", "data"],
  ]);
});

test("reload builds a fresh modular context and keeps updated fallback connections", () => {
  const { calls, runtime, compatibility } = setup();
  assert.equal(runtime.load(), "loaded");
  const first = calls[0],
    previousLoad = () => {};
  runtime.connect({ ...compatibility, previousLoad });
  runtime.load();
  assert.notEqual(calls[1], first);
  assert.equal(calls[1].previousLoad, previousLoad);
  calls[1].render.ixs("new");
  assert.deepEqual(calls[2], ["ixs", "new"]);
});
