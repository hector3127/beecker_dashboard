import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const scope = { el: (_tag, props) => props };
vm.runInNewContext(
  fs
    .readFileSync(
      "frontend/static/scripts/pages/project_detail/sections/ixs_client_actions.js",
      "utf8",
    )
    .replace(/^import.*;$/gm, "")
    .replace("export function", "function"),
  scope,
);
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((a, b) => {
    resolve = a;
    reject = b;
  });
  return { promise, resolve, reject };
};
const setup = () => {
  const target = {
      replaceChildren(...nodes) {
        this.nodes = nodes;
      },
    },
    cache = {},
    applied = [];
  const args = {
    project: { proyecto: { id: "AMK.008", nombre: "Proyecto IXB" } },
    target,
    cache,
    tab: "cliente",
    current: () => true,
    apply: (x) => applied.push(x),
  };
  return { target, cache, applied, args };
};

test("Client/Actions preserves transport failure text and allows retry", async () => {
  const s = setup();
  let fail = true;
  const loader = scope.createClientActionsLoader({
    client: async () => {
      if (fail) throw new Error("Sin conexión");
      return { ok: true, proyectoId: "AMK.008" };
    },
  });
  await loader.load(s.args);
  assert.equal(
    s.target.textContent,
    "No se pudo consultar Cliente y Acciones: Sin conexión",
  );
  fail = false;
  await loader.load(s.args);
  assert.equal(s.applied.length, 1);
});

test("Client/Actions uses resource API and retains project metadata and cache", async () => {
  const s = setup(),
    calls = [];
  const loader = scope.createClientActionsLoader({
    client: async (id) => {
      calls.push(id);
      return { ok: true, proyectoId: id, partes: [] };
    },
  });
  await loader.load(s.args);
  assert.equal(s.applied[0].proyecto, s.args.project.proyecto);
  await loader.load({ ...s.args, tab: "acciones" });
  assert.deepEqual(calls, ["AMK.008"]);
  assert.equal(s.applied.length, 2);
});
test("Client/Actions preserves invalid-project and failure messages, and retry", async () => {
  const s = setup();
  let result = { ok: true, proyectoId: "AJENO" };
  const loader = scope.createClientActionsLoader({
    client: async () => result,
  });
  await loader.load(s.args);
  assert.match(s.target.nodes[0].text, /respuesta de proyecto inválida/);
  assert.equal(s.applied.length, 0);
  result = { ok: false, error: "Sin hoja" };
  await loader.load(s.args);
  assert.match(s.target.nodes[0].text, /Sin hoja/);
  result = { ok: true, proyectoId: "AMK.008" };
  await loader.load(s.args);
  assert.equal(s.applied.length, 1);
});
test("Client/Actions ignores old success and failure replies after new load", async () => {
  for (const failure of [false, true]) {
    const s = setup(),
      first = deferred();
    let count = 0;
    const loader = scope.createClientActionsLoader({
      client: () =>
        ++count === 1
          ? first.promise
          : Promise.resolve({
              ok: true,
              proyectoId: "AMK.008",
              version: "new",
            }),
    });
    const old = loader.load(s.args);
    await loader.load(s.args);
    if (failure) first.reject(new Error("Viejo"));
    else first.resolve({ ok: true, proyectoId: "AMK.008", version: "old" });
    await old;
    assert.equal(s.applied.length, 1);
    assert.equal(s.applied[0].version, "new");
    assert.equal(s.target.textContent, undefined);
  }
});
test("Client/Actions ignores responses after leaving project/tab", async () => {
  const s = setup(),
    pending = deferred();
  let active = true;
  const loader = scope.createClientActionsLoader({
    client: () => pending.promise,
  });
  const task = loader.load({ ...s.args, current: () => active });
  active = false;
  pending.resolve({ ok: true, proyectoId: "AMK.008" });
  await task;
  assert.equal(s.applied.length, 0);
});
