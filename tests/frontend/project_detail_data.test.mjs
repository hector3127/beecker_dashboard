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

test("AER risks preserve encoded project, operation, body and shared timeout", async () => {
  const reads = [],
    writes = [],
    result = { ok: true, riesgos: {} };
  const data = context.createProjectData(
    async (...args) => {
      reads.push(args);
      return { data: result };
    },
    async (...args) => {
      writes.push(args);
      return { data: result };
    },
  );
  assert.equal(await data.aerRisks("AER.001 | CR"), result);
  const body = { UID: "risk/'1", Riesgo: "Texto" };
  for (const operation of ["guardar", "eliminar", "limpiar-duplicados"])
    assert.equal(
      await data.saveAerRisk("AER.001 | CR", operation, body),
      result,
    );
  assert.equal(
    reads[0][0],
    "screens/proyectos/AER.001%20%7C%20CR/riesgos-aer/",
  );
  assert.equal(reads[0][2].timeout, 90000);
  for (const [index, operation] of [
    "guardar",
    "eliminar",
    "limpiar-duplicados",
  ].entries()) {
    assert.equal(writes[index][0], "POST");
    assert.equal(
      writes[index][1],
      `screens/proyectos/AER.001%20%7C%20CR/riesgos-aer/${operation}/`,
    );
    assert.equal(writes[index][2], body);
    assert.equal(writes[index][3].timeout, 90000);
  }
});

test("AER record ranges use exact dates and encoded project via GET", async () => {
  const calls = [];
  const api = context.createProjectData(async (...args) => {
    calls.push(args);
    return { data: { ok: true, registros: [] } };
  });
  await api.aerRecords("AER.001 | CR", "2026-10-01", "2026-10-24");
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [
    [
      "screens/proyectos/AER.001%20%7C%20CR/aer/registros/",
      { desde: "2026-10-01", hasta: "2026-10-24" },
      { timeout: 90000 },
    ],
  ]);
});

test("AER planning writes preserve encoded project, body and timeout", async () => {
  const calls = [];
  const api = context.createProjectData(null, async (...args) => {
    calls.push(args);
    return { data: { ok: true } };
  });
  const body = { uid: "a'1", cerrado: false };
  assert.deepEqual(await api.saveAerPlan("AER.001 | CR", "cerrar", body), {
    ok: true,
  });
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [
    [
      "POST",
      "screens/proyectos/AER.001%20%7C%20CR/planeacion-aer/cerrar/",
      body,
      { timeout: 90000 },
    ],
  ]);
});

test("Actions use encoded project paths, family and exact POST bodies", async () => {
  const reads = [],
    writes = [];
  const api = context.createProjectData(
    async (...args) => {
      reads.push(args);
      return { data: { ok: true } };
    },
    async (...args) => {
      writes.push(args);
      return { data: { ok: true } };
    },
  );
  await api.actions("AMK.008 | CR", "ixs");
  await api.actions("AMK.008 | CR", "aer", true);
  const body = {
    servicio: "aer",
    uid: "1",
    campo: "estado",
    valor: "Completado",
  };
  await api.saveAction("AMK.008 | CR", "actualizar", body);
  assert.deepEqual(JSON.parse(JSON.stringify(reads)), [
    [
      "screens/proyectos/AMK.008%20%7C%20CR/acciones/",
      { servicio: "ixs" },
      { timeout: 90000 },
    ],
    [
      "screens/proyectos/AMK.008%20%7C%20CR/acciones/partes/",
      { servicio: "aer" },
      { timeout: 90000 },
    ],
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(writes)), [
    [
      "POST",
      "screens/proyectos/AMK.008%20%7C%20CR/acciones/actualizar/",
      body,
      { timeout: 90000 },
    ],
  ]);
});

test("IA actions preserve exact bodies, project encoding and shared POST client", async () => {
  const calls = [];
  const api = context.createProjectData(null, async (...args) => {
    calls.push(args);
    return { data: { ok: true } };
  });
  const id = "CCO.001 | CR",
    ctx = { horas: 4 };
  await api.aiAnalyze(id, ctx, true);
  await api.aiAsk(id, ctx, "Pregunta");
  await api.aiSaveMemory(id, ctx, { resumen: [] });
  await api.aiSaveMinute(id, "Tema", "2026-10-23", "Contenido");
  await api.aiSaveFolder(id, "https://drive.google.com/folder", "documentos");
  await api.aiRemoveFolder(id, "folder", "transcripciones");
  await api.aiReadDocument(id, "file");
  await api.aiGenerateMinute(id, ["file"], "Tema", "2026-10-23", "Notas");
  await api.aiSaveAction(id, { Accion: "Revisar" });
  const expected = [
    ["analizar", { contexto: ctx, forzar: true }],
    ["preguntar", { contexto: ctx, pregunta: "Pregunta" }],
    ["memoria/guardar", { snapshot: ctx, analisis: { resumen: [] } }],
    [
      "minutas/guardar",
      { tema: "Tema", fecha: "2026-10-23", contenido: "Contenido" },
    ],
    [
      "drive/carpetas/guardar",
      { url: "https://drive.google.com/folder", tipo: "documentos" },
    ],
    ["drive/carpetas/quitar", { carpeta: "folder", tipo: "transcripciones" }],
    ["drive/documento/leer", { archivo: "file" }],
    [
      "drive/minuta/generar",
      { archivos: ["file"], tema: "Tema", fecha: "2026-10-23", notas: "Notas" },
    ],
    ["accion/guardar", { Accion: "Revisar" }],
  ];
  assert.deepEqual(
    JSON.parse(JSON.stringify(calls)),
    expected.map(([path, payload]) => [
      "POST",
      `screens/proyectos/CCO.001%20%7C%20CR/ia/${path}/`,
      payload,
      { timeout: 90000 },
    ]),
  );
});

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
