import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const context = {};
vm.runInNewContext(
  fs
    .readFileSync(
      "frontend/static/scripts/pages/project_detail/sections/ixs_ai_sources.js",
      "utf8",
    )
    .replace("export function", "function"),
  context,
);
const state = () => ({
  id: "AMK.008",
  request: 0,
  sourceErrors: {},
  minutas: [],
  analisis: null,
  loading: false,
  driveLoading: false,
  driveSelected: ["t", "d", "missing"],
  driveFiles: [],
});
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((a, b) => {
    resolve = a;
    reject = b;
  });
  return { promise, resolve, reject };
};

test("six independent sources retain successes, partial errors and retry", async () => {
  const s = state(),
    calls = [],
    painted = [];
  const methods = [
    "planningAzure",
    "planning",
    "resources",
    "records",
    "client",
    "raidRegistry",
  ];
  const api = Object.fromEntries(
    methods.map((method) => [
      method,
      async (id) => {
        calls.push([method, id]);
        return method === "records"
          ? { ok: false, error: "Clockify" }
          : { ok: true, source: method };
      },
    ]),
  );
  const controller = context.createAiSources(api),
    guards = { current: () => true, paint: () => painted.push(true) };
  await controller.sources(s, guards);
  assert.equal(calls.length, 6);
  assert.ok(calls.every((x) => x[1] === "AMK.008"));
  assert.equal(s.azure.source, "planningAzure");
  assert.equal(s.sourceErrors.clockify, "Clockify");
  assert.equal(painted.length, 6);
  api.records = async () => ({ ok: true, registros: [] });
  await controller.sources(s, guards);
  assert.equal(s.sourceErrors.clockify, undefined);
});

test("stale successes and failures never replace a newer sources load", async () => {
  const s = state(),
    old = deferred();
  let version = 0;
  const api = Object.fromEntries(
    [
      "planningAzure",
      "planning",
      "resources",
      "records",
      "client",
      "raidRegistry",
    ].map((key) => [
      key,
      () => (version ? Promise.resolve({ ok: true, version }) : old.promise),
    ]),
  );
  const controller = context.createAiSources(api),
    guards = { current: () => true, paint: () => {} };
  const pending = controller.sources(s, guards);
  version = 1;
  await controller.sources(s, guards);
  old.reject(new Error("Old failure"));
  await pending;
  assert.equal(s.azure.version, 1);
  assert.deepEqual(s.sourceErrors, {});
});

test("history restores saved analysis only when no new analysis is present or running", async () => {
  for (const mode of ["saved", "current", "running"]) {
    const s = state();
    if (mode === "current") s.analisis = { current: true };
    if (mode === "running") s.loading = true;
    const api = {
      aiMemory: async () => ({ ok: true, actual: {} }),
      aiMinutes: async () => ({ ok: true, filas: [{ tema: "Minuta" }] }),
      aiAnalysis: async () => ({
        ok: true,
        analisis: { resumen: ["Saved"] },
        fecha: "corte",
        desdeMemoria: true,
      }),
    };
    await context
      .createAiSources(api)
      .history(s, { current: () => true, paint: () => {} });
    assert.equal(s.minutas[0].tema, "Minuta");
    if (mode === "saved") assert.equal(s.analisis.desdeMemoria, true);
    if (mode === "current") assert.equal(s.analisis.current, true);
    if (mode === "running") assert.equal(s.analisis, null);
  }
});

test("Drive lists only configured folders and keeps only selected transcripts", async () => {
  const s = state(),
    calls = [];
  const api = {
    aiDriveFolders: async () => ({ ok: true, carpetas: ["folder"] }),
    aiDriveFiles: async (id) => {
      calls.push(id);
      return {
        ok: true,
        limited: true,
        files: [
          { id: "t", tipo: "transcripciones" },
          { id: "d", tipo: "documentos" },
        ],
      };
    },
  };
  await context
    .createAiSources(api)
    .drive(s, { current: () => true, paint: () => {} });
  assert.deepEqual(calls, ["AMK.008"]);
  assert.equal(JSON.stringify(s.driveSelected), '["t"]');
  assert.equal(s.driveError, "Se muestran los primeros 250 archivos.");
  api.aiDriveFolders = async () => ({
    ok: true,
    carpetas: [],
    transcripciones: [],
  });
  await context
    .createAiSources(api)
    .drive(s, { current: () => true, paint: () => {} });
  assert.equal(calls.length, 1);
  assert.equal(s.driveFiles.length, 0);
});

test("Drive duplicate loads and replies for a different project are ignored", async () => {
  const s = state(),
    pending = deferred();
  let current = true,
    calls = 0;
  const api = {
    aiDriveFolders: () => {
      calls++;
      return pending.promise;
    },
    aiDriveFiles: () => assert.fail("Files should not load"),
  };
  const controller = context.createAiSources(api),
    guards = { current: () => current, paint: () => {} };
  const first = controller.drive(s, guards);
  await controller.drive(s, guards);
  assert.equal(calls, 1);
  current = false;
  pending.resolve({ ok: true, carpetas: ["folder"] });
  await first;
  assert.equal(s.driveConfig, undefined);
});
