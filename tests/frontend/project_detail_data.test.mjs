import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const code = fs
  .readFileSync("frontend/static/scripts/pages/project_detail/data.js", "utf8")
  .replace(/import[^;]+;/, "")
  .replace("export function", "function");
const context = {};
vm.runInNewContext(code, context);

test("project reads keep exact IDs, payloads and the previous 90 second timeout", async () => {
  const calls = [];
  const payload = { horas: 23.75, cerrado: true };
  const data = context.createProjectData(async (...args) => {
    calls.push(args);
    return { data: payload, meta: {} };
  });
  assert.equal(await data.filters(), payload);
  assert.equal(await data.dashboard("CCO.001 | CR", false), payload);
  assert.equal(await data.dashboard("AER.001", true), payload);
  for (const method of ["raid", "tasks", "stages", "resources", "records"]) {
    assert.equal(await data[method]("CCO.001 | CR"), payload);
  }
  assert.deepEqual(
    calls.map((call) => call[0]),
    [
      "screens/proyectos/filtros/",
      "screens/proyectos/CCO.001%20%7C%20CR/ejecutivo/",
      "screens/proyectos/AER.001/aer/",
      "screens/proyectos/CCO.001%20%7C%20CR/raid/",
      "screens/proyectos/CCO.001%20%7C%20CR/tasks/",
      "screens/proyectos/CCO.001%20%7C%20CR/etapas/",
      "screens/proyectos/CCO.001%20%7C%20CR/recursos/",
      "screens/proyectos/CCO.001%20%7C%20CR/registros/",
    ],
  );
  for (const call of calls) {
    assert.equal(call[1], undefined);
    assert.equal(call[2].timeout, 90000);
  }
});

test("failed reads propagate their error and a later retry can recover", async () => {
  const failure = new Error("source");
  let calls = 0;
  const data = context.createProjectData(async () => {
    if (++calls === 1) throw failure;
    return { data: { ok: true } };
  });
  await assert.rejects(data.dashboard("AER.001", true), (e) => e === failure);
  assert.equal((await data.dashboard("AER.001", true)).ok, true);
  assert.equal(calls, 2);
});
