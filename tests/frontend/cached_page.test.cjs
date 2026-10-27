const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const previous = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, "frozen/cached_page_previous.json"),
    "utf8",
  ),
);
const source = fs.readFileSync(
  "frontend/static/scripts/pages/executive/sections/cut.js",
  "utf8",
);
const transport = fs.readFileSync(
  "frontend/static/scripts/data/api-client.js",
  "utf8",
);
const plain = (value) => JSON.parse(JSON.stringify(value));
const full = {
  loadedAt: "2026-10-22T10:00:00-06:00",
  operations: { projects: 10 },
  commercial: { won: 100 },
  costs: { projects: [{ id: "P" }], pending: 0 },
};
const blocks = { financial: true, operations: true, commercial: true };
function harness(states, { model = full, postFailures = 0 } = {}) {
  const requests = [],
    timers = new Map(),
    loading = new Set(["revenue"]);
  let nextTimer = 0,
    reloads = 0,
    finished = 0;
  const control = { disabled: false, textContent: "" },
    status = { textContent: "" };
  const location = new URL(
    "http://localhost/?periodo=mes&anio=2026&mes=9&buscar=ACME",
  );
  location.reload = () => {
    reloads++;
  };
  const period = { periodo: "mes", anio: "2026", mes: "9" },
    data = structuredClone(model);
  const context = {
    URL,
    URLSearchParams,
    AbortController,
    AbortSignal,
    setTimeout,
    clearTimeout,
    location,
    console,
    config: { apiBase: "/api/v1/", csrfCookie: "csrftoken" },
    document: {
      cookie: "csrftoken=csrf-token",
      getElementById: (id) =>
        id === "executive-prepare"
          ? control
          : id === "executive-cut-status"
            ? status
            : null,
    },
    setInterval(callback) {
      const id = ++nextTimer;
      timers.set(id, callback);
      return id;
    },
    clearInterval: (id) => timers.delete(id),
    finishLoading(set) {
      finished++;
      set.clear();
    },
    fetch: async (url, options) => {
      requests.push({ url: String(url), options });
      let result;
      if (options.method === "POST") {
        if (postFailures-- > 0) throw Error("offline");
        result = { state: "queued" };
      } else {
        result = states.shift();
        if (result instanceof Error) throw result;
        if (!result) throw Error("Unexpected read");
      }
      return {
        ok: true,
        status: 200,
        headers: { get: () => "application/json" },
        json: async () => ({ data: result }),
      };
    },
  };
  vm.createContext(context);
  vm.runInContext(
    transport.replace(/^import.*;$/gm, "").replaceAll("export ", ""),
    context,
  );
  vm.runInContext(
    source.replace(/^import.*;$/gm, "").replaceAll("export ", ""),
    context,
  );
  context.mountCut({ model: data, loading, period });
  return {
    requests,
    timers,
    control,
    status,
    location,
    model: data,
    loading,
    reloads: () => reloads,
    finished: () => finished,
    async tick() {
      for (const callback of [...timers.values()]) await callback();
    },
  };
}
const settle = () => new Promise((resolve) => setImmediate(resolve));
test("refresh prepares the new cut without resetting the visible page or filters", async () => {
  const h = harness([
    { state: "running", blocks },
    { state: "ready", blocks },
  ]);
  const before = plain(h.model),
    href = h.location.href;
  assert.equal(h.requests.length, 0, "a loaded page does not refresh itself");
  await h.control.onclick();
  assert.equal(h.reloads(), previous.genericReady.reloadsBefore);
  assert.equal(h.control.disabled, true);
  assert.equal(h.timers.size, 1);
  assert.deepEqual(h.model, before);
  assert.equal(h.location.href, href);
  await h.tick();
  assert.equal(h.reloads(), previous.genericReady.reloadsAfter);
  assert.equal(h.location.href, href);
  assert.deepEqual(h.model, before);
  assert.equal(h.timers.size, 0);
});
test("failed source refresh keeps the old cut and offers a retry", async () => {
  const h = harness([
    { state: "failed", blocks },
    { state: "ready", blocks },
  ]);
  const before = plain(h.model);
  await h.control.onclick();
  assert.equal(h.reloads(), previous.genericFailure.reloads);
  assert.equal(h.control.disabled, false);
  assert.match(h.status.textContent, /Se conserva el corte/);
  assert.equal(h.timers.size, 0, "a failed refresh must not restart polling");
  assert.deepEqual(h.model, before);
  await h.control.onclick();
  assert.equal(h.reloads(), 1);
  const offline = harness([{ state: "ready", blocks }], { postFailures: 1 });
  await offline.control.onclick();
  assert.equal(offline.reloads(), 0);
  assert.equal(offline.control.disabled, false);
  assert.equal(offline.timers.size, 0);
  assert.match(offline.status.textContent, /No se pudo iniciar/);
  await offline.control.onclick();
  assert.equal(offline.reloads(), 1);
});
test("executive refresh polls a light status endpoint and retains dates and CSRF", async () => {
  const h = harness([
    { state: "running", blocks },
    { state: "ready", blocks },
  ]);
  await h.control.onclick();
  assert.equal(h.reloads(), 0);
  await h.tick();
  assert.deepEqual(
    h.requests.map((x) => x.options.method),
    previous.poll.methods,
  );
  for (const { url, options } of h.requests) {
    const target = new URL(url);
    assert.equal(target.pathname, "/api/v1/screens/executive/actualizar/");
    assert.equal(target.searchParams.get("periodo"), "mes");
    assert.equal(target.searchParams.get("anio"), "2026");
    assert.equal(target.searchParams.get("mes"), "9");
    assert.equal(options.credentials, "same-origin");
  }
  assert.equal(
    h.requests[0].options.headers["X-CSRFToken"],
    previous.poll.csrf,
  );
  for (const request of h.requests.slice(1))
    assert.equal(request.options.cache, previous.poll.cache);
  assert.equal(h.reloads(), 1);
  assert.equal(h.timers.size, 0);
});
test("executive partial and failed refreshes do not claim a complete cut", async () => {
  const partial = harness(
    [
      {
        state: "ready",
        partial: true,
        blocks: { ...blocks, operations: false },
      },
    ],
    { model: { ...full, operations: { projects: null } } },
  );
  await settle();
  assert.equal(partial.reloads(), previous.partial.reloads);
  assert.match(partial.status.textContent, /pendientes identificados/);
  assert.equal(partial.control.textContent, "Ver corte preparado");
  assert.equal(partial.timers.size, 0);
  await partial.control.onclick();
  assert.equal(partial.reloads(), 1);
  const failed = harness(
    [{ state: "failed", blocks: { ...blocks, operations: false } }],
    { model: { ...full, operations: { projects: null } } },
  );
  await settle();
  assert.equal(failed.reloads(), previous.failure.reloads);
  assert.match(failed.status.textContent, /Se conserva el corte/);
  assert.equal(failed.control.disabled, false);
  assert.equal(failed.timers.size, 0);
  const financial = harness([
    { state: "ready", partial: true, blocks: { ...blocks, financial: false } },
  ]);
  await financial.control.onclick();
  assert.equal(financial.reloads(), 0);
  assert.match(
    financial.status.textContent,
    /no se mostrarán cifras inventadas/,
  );
  assert.equal(financial.control.disabled, false);
  assert.equal(financial.timers.size, 0);
  const network = harness([Error("offline")]);
  await network.control.onclick();
  assert.equal(network.reloads(), 0);
  assert.match(network.status.textContent, /Se conserva el corte/);
  assert.equal(network.timers.size, 0);
});
