import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const code = fs
  .readFileSync("frontend/static/scripts/pages/project_detail/data.js", "utf8")
  .replace(/import[^;]+;/, "")
  .replace("export function", "function");
const context = {
  apiSend: () => {
    throw new Error("Unexpected write");
  },
};
vm.runInNewContext(code, context);

test("IA reads use resource endpoints, exact identifiers and the existing timeout", async () => {
  const calls = [];
  const api = context.createProjectData(async (...args) => {
    calls.push(args);
    return { data: { ok: true } };
  });
  for (const name of [
    "client",
    "aiAnalysis",
    "aiMemory",
    "aiMinutes",
    "aiDriveFolders",
    "aiDriveFiles",
  ])
    await api[name]("CCO.001 | CR");
  assert.deepEqual(
    calls.map((x) => x[0]),
    [
      "cliente/",
      "ia/analisis/",
      "ia/memoria/",
      "ia/minutas/",
      "ia/drive/carpetas/",
      "ia/drive/archivos/",
    ].map((path) => "screens/proyectos/CCO.001%20%7C%20CR/" + path),
  );
  assert.ok(calls.every((x) => x[1] === undefined && x[2].timeout === 90000));
});

test("Azure tab sends the exact project and explicit refresh without changing planning", async () => {
  const calls = [];
  const data = context.createProjectData(async (...args) => {
    calls.push(args);
    return { data: { ok: true } };
  });
  await data.azure("CCO.001 | CR");
  await data.azure("CCO.001 | CR", true);
  await data.planningAzure("CCO.001 | CR");
  assert.equal(calls[0][0], "screens/proyectos/CCO.001%20%7C%20CR/azure/");
  assert.equal(calls[0][1], undefined);
  assert.equal(calls[1][1].forzar, "1");
  assert.equal(
    calls[2][0],
    "screens/proyectos/CCO.001%20%7C%20CR/planeacion/azure/",
  );
  assert.equal(calls[2][1], undefined);
  assert.ok(calls.every((call) => call[2].timeout === 90000));
});

test("work item writes preserve IDs, typed values, body and timeout", async () => {
  const calls = [];
  const data = context.createProjectData(
    () => {
      throw Error("Unexpected read");
    },
    async (...args) => {
      calls.push(args);
      return { data: { ok: true } };
    },
  );
  await data.saveWorkItem(101, "qa", false);
  await data.saveWorkItem(101, "devConstruido", 0);
  await data.commentWorkItem(202, "Texto á ' \n");
  assert.equal(calls[0][1], "screens/work-items/101/avance/");
  assert.equal(calls[0][2].valor, false);
  assert.equal(calls[1][2].valor, 0);
  assert.equal(calls[2][1], "screens/work-items/202/comentarios/");
  assert.equal(calls[2][2].comentario, "Texto á ' \n");
  for (const call of calls) {
    assert.equal(call[0], "POST");
    assert.equal(call[3].timeout, 90000);
  }
});

test("resource writes keep exact IDs, payloads and timeout through the shared client", async () => {
  const calls = [],
    payload = {
      idProyecto: "CCO.001 | CR",
      nombre: "O'Connor",
      rol: "QA",
      horasEstimadas: "0",
      activo: false,
    };
  const saved = { ok: true, proyectoId: payload.idProyecto, filas: [] };
  const data = context.createProjectData(
    () => {
      throw new Error("Unexpected read");
    },
    async (...args) => {
      calls.push(args);
      return { data: saved, meta: {} };
    },
  );
  assert.equal(await data.saveResource(payload.idProyecto, payload), saved);
  assert.equal(calls[0][0], "POST");
  assert.equal(
    calls[0][1],
    "screens/proyectos/CCO.001%20%7C%20CR/recursos/guardar/",
  );
  assert.equal(calls[0][2], payload);
  assert.equal(calls[0][3].timeout, 90000);
});

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
  for (const method of [
    "raid",
    "tasks",
    "stages",
    "resources",
    "records",
    "planning",
    "planningAzure",
  ]) {
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
      "screens/proyectos/CCO.001%20%7C%20CR/planeacion/",
      "screens/proyectos/CCO.001%20%7C%20CR/planeacion/azure/",
    ],
  );
  for (const call of calls) {
    assert.equal(call[1], undefined);
    assert.equal(call[2].timeout, 90000);
  }
});

test("planning mutations preserve type, exact UID and use POST with the shared timeout", async () => {
  const calls = [],
    payload = {
      idProyecto: "CCO.001 | CR",
      uid: "uid/'a",
      fecha: "2026-10-23",
    };
  const result = { ok: false, error: "Registro no encontrado." };
  const data = context.createProjectData(
    () => {
      throw Error("Unexpected read");
    },
    async (...args) => {
      calls.push(args);
      return { data: result };
    },
  );
  assert.equal(await data.savePlan("compromiso", payload), result);
  assert.equal(
    await data.deletePlan("vacacion", payload.idProyecto, payload.uid),
    result,
  );
  assert.equal(
    calls[0][1],
    "screens/proyectos/CCO.001%20%7C%20CR/planeacion/compromiso/guardar/",
  );
  assert.equal(calls[0][2], payload);
  assert.equal(
    calls[1][1],
    "screens/proyectos/CCO.001%20%7C%20CR/planeacion/vacacion/eliminar/",
  );
  assert.equal(calls[1][2].uid, payload.uid);
  for (const call of calls) {
    assert.equal(call[0], "POST");
    assert.equal(call[3].timeout, 90000);
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
