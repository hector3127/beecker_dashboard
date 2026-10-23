import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const directory = "frontend/static/scripts/pages/project_detail/sections/";
function environment() {
  const messages = [];
  const context = { azureMessage: (...args) => messages.push(args) };
  for (const file of ["ixs_azure_model.js", "ixs_azure.js"]) {
    vm.runInNewContext(
      fs
        .readFileSync(directory + file, "utf8")
        .replace(/^import.*;$/gm, "")
        .replaceAll("export function", "function"),
      context,
    );
  }
  return { context, messages };
}
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
};

test("panel shape retains arrays, notice and empty-array fallbacks without mutation", () => {
  const { context } = environment();
  const items = [{ id: 1 }];
  const raw = { items, allItems: null, stale: "bad", aviso: "Corte" };
  const panel = context.azurePanel(raw, "AMK.008", 4);
  assert.equal(panel.items, items);
  assert.equal(panel.allItems.length, 0);
  assert.equal(panel.stale.length, 0);
  assert.equal(panel.notice, "Corte");
  assert.equal(panel.requestId, 4);
  assert.equal(panel.projectId, "AMK.008");
  assert.equal(raw.allItems, null);
});

test("latest refresh wins even when earlier calls finish last", async () => {
  const { context, messages } = environment();
  const first = deferred(),
    second = deferred(),
    calls = [],
    rendered = [];
  const controller = context.createAzureController({
    azure: (...args) => {
      calls.push(args);
      return calls.length === 1 ? first.promise : second.promise;
    },
  });
  const root = { isConnected: true },
    project = { proyecto: { id: "AMK.008" } },
    state = { requestId: 0 };
  const guards = {
    current: () => true,
    active: () => true,
    loaded: (x) => rendered.push(x),
  };
  const old = controller.load(root, project, state, false, guards);
  const fresh = controller.load(root, project, state, true, guards);
  second.resolve({ ok: true, aviso: "Actual" });
  await fresh;
  first.resolve({ ok: true, aviso: "Viejo" });
  await old;
  assert.deepEqual(
    calls.map((x) => x[1]),
    [false, true],
  );
  assert.equal(rendered.length, 1);
  assert.equal(rendered[0].notice, "Actual");
  assert.equal(messages.length, 2);
});

for (const mode of ["inactive", "different-project", "detached"]) {
  test(`late failure is ignored when ${mode}`, async () => {
    const { context, messages } = environment(),
      pending = deferred();
    let active = true,
      same = true;
    const root = { isConnected: true };
    const controller = context.createAzureController({
      azure: () => pending.promise,
    });
    const done = controller.load(
      root,
      { proyecto: { id: "AMK.008" } },
      { requestId: 0 },
      false,
      {
        active: () => active,
        current: () => same,
        loaded: () => assert.fail("stale render"),
      },
    );
    if (mode === "inactive") active = false;
    if (mode === "different-project") same = false;
    if (mode === "detached") root.isConnected = false;
    pending.reject(new Error("Old failure"));
    await done;
    assert.equal(messages.length, 1);
  });
}
