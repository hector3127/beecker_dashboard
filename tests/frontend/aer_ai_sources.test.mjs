import test from "node:test";
import assert from "node:assert/strict";
import { createAerAiSources } from "../../frontend/static/scripts/pages/project_detail/sections/aer_ai_sources.js";
function setup(api) {
  const state = {
    id: "AER.001",
    minutas: null,
    config: null,
    archivos: null,
    seleccion: ["old"],
  };
  let live = true,
    active = true,
    paints = 0,
    opened = 0;
  const toasts = [];
  const controller = createAerAiSources(api).bind({
    id: state.id,
    state,
    current: () => live,
    active: () => active,
    paint: () => paints++,
    context: () => ({ id: "AER.001", k: { horas: 20 } }),
    toast: (...args) => toasts.push(args),
    openConfig: () => opened++,
  });
  return {
    state,
    controller,
    toasts,
    stale: () => (live = false),
    inactive: () => (active = false),
    paints: () => paints,
    opened: () => opened,
  };
}
test("Cached reads preserve consultation flags and do not repeat requests", async () => {
  const calls = [];
  const x = setup({
    aerAiSource: async (id, source, context) => {
      calls.push([id, source, context]);
      return {
        ok: true,
        resultado: { analisis: { resumen: [] } },
        resumen: { contenido: "Guardado" },
        filas: [],
        config: {},
      };
    },
  });
  await Promise.all([
    x.controller.analysis(),
    x.controller.summary(),
    x.controller.minutes(),
    x.controller.config(),
  ]);
  assert.equal(calls.length, 4);
  assert.equal(x.state.analisis.restaurado, true);
  assert.equal(x.state.resumenConsultado, true);
  assert.equal(x.state.analisisConsultado, true);
  await Promise.all([
    x.controller.analysis(),
    x.controller.summary(),
    x.controller.minutes(),
    x.controller.config(true),
  ]);
  assert.equal(calls.length, 4);
  assert.equal(x.opened(), 1);
});
for (const method of ["analysis", "summary", "minutes", "config", "files"])
  test(`Late ${method} response cannot mutate replaced state`, async () => {
    let resolve;
    const x = setup({ aerAiSource: () => new Promise((r) => (resolve = r)) });
    if (method === "files")
      x.state.config = { folderUrl: "folder", nombreFrecuente: "Minutes" };
    const pending = x.controller[method]();
    x.stale();
    const before = JSON.stringify(x.state),
      paints = x.paints();
    resolve({
      ok: true,
      resultado: { analisis: {} },
      resumen: {},
      config: {},
      filas: [],
      totalEncontradas: 5,
    });
    await pending;
    assert.equal(JSON.stringify(x.state), before);
    assert.equal(x.paints(), paints);
    assert.equal(x.toasts.length, 0);
  });
test("Analysis restoration never overwrites a freshly generated analysis", async () => {
  let resolve;
  const x = setup({ aerAiSource: () => new Promise((r) => (resolve = r)) });
  const pending = x.controller.analysis();
  x.state.analisis = { analisis: { resumen: ["New"] } };
  resolve({ ok: true, resultado: { analisis: { resumen: ["Old"] } } });
  await pending;
  assert.deepEqual(x.state.analisis, { analisis: { resumen: ["New"] } });
});
test("Configured Drive loads once and retains original selection/display rules", async () => {
  const calls = [];
  const x = setup({
    aerAiSource: async (id, name) => {
      calls.push(name);
      return name === "config"
        ? {
            ok: true,
            config: { folderUrl: "folder", nombreFrecuente: "Minutes" },
          }
        : { ok: true, totalEncontradas: 2, archivos: [] };
    },
  });
  await x.controller.config();
  await new Promise((r) => setTimeout(r, 0));
  assert.deepEqual(calls, ["config", "archivos"]);
  assert.equal(x.state.mostrarArchivos, true);
  assert.equal(x.state.archivosOcultos, false);
  assert.deepEqual(x.state.seleccion, []);
});
test("Drive failure can retry and does not erase previous files", async () => {
  let fail = true;
  const x = setup({
    aerAiSource: async () => {
      if (fail) throw Error("Unavailable");
      return { ok: true, totalEncontradas: 0 };
    },
  });
  x.state.config = { folderUrl: "folder", nombreFrecuente: "Minutes" };
  x.state.archivos = { old: true };
  await x.controller.files();
  assert.equal(x.state.errorBusqueda, "Unavailable");
  assert.deepEqual(x.state.archivos, { old: true });
  assert.equal(x.state.buscando, false);
  fail = false;
  await x.controller.files();
  assert.equal(x.state.errorBusqueda, "");
  assert.equal(x.state.archivos.totalEncontradas, 0);
});
