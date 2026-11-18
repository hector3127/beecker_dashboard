const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
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
test("prepared data keeps the visible page and filters without refresh writes", async () => {
  const h = harness([]);
  const before = plain(h.model), href = h.location.href;
  await settle();
  assert.equal(h.requests.length, 0);
  assert.equal(h.control.onclick, undefined);
  assert.equal(h.reloads(), 0);
  assert.equal(h.timers.size, 0);
  assert.deepEqual(h.model, before);
  assert.equal(h.location.href, href);
});
test("missing blocks poll with dates and reload once the prepared cut is ready", async () => {
  const h = harness([{state:"running",blocks:{...blocks,commercial:false}}, {state:"ready",blocks}], {model:{...full,commercial:null}});
  const href = h.location.href;
  await settle();
  assert.equal(h.reloads(), 0);
  await h.tick();
  assert.deepEqual(h.requests.map(x => x.options.method), ["GET","GET"]);
  for (const {url,options} of h.requests) {
    const target = new URL(url);
    assert.equal(target.pathname,"/api/v1/screens/executive/actualizar/");
    assert.equal(target.searchParams.get("periodo"),"mes");
    assert.equal(target.searchParams.get("mes"),"9");
    assert.equal(options.credentials,"same-origin");
    assert.equal(options.cache,"no-store");
  }
  assert.equal(h.reloads(),1);
  assert.equal(h.timers.size,0);
  assert.equal(h.location.href,href);
});
test("failed preparation or network stops polling and preserves existing data", async () => {
  for (const state of [{state:"failed",blocks:{}}, Error("offline")]) {
    const h = harness([state], {model:{...full,commercial:null}});
    const before = plain(h.model);
    await settle();
    assert.equal(h.reloads(),0);
    assert.match(h.status.textContent,/Se conserva el corte/);
    assert.equal(h.timers.size,0);
    assert.deepEqual(h.model,before);
    assert.equal(h.requests[0].options.method,"GET");
  }
});
test("partial cuts preserve pending coverage instead of claiming completeness", async () => {
  const h = harness([{state:"ready",partial:true,blocks:{...blocks,operations:false}}], {model:{...full,operations:{projects:null}}});
  await settle();
  assert.equal(h.reloads(),0);
  assert.match(h.status.textContent,/datos pendientes/);
  assert.equal(h.timers.size,0);
  assert.equal(h.finished(),1);
});

test("idle and busy refreshes stop polling and offer retry", async () => {
  for (const state of ["idle", "busy"]) {
    const page = harness([{ state }], { model: { ...full, loadedAt: null } });
    await settle();
    assert.equal(page.timers.size, 0);
    assert.equal(page.control.disabled, false);
    assert.match(page.status.textContent, /periodo de nuevo/);
  }
});


test("failed monthly preparation removes the consulting state", () => {
  const nodes = new Map([
    ["monthly-profit-state", { textContent: "Consultando", classList: { contains: () => false } }],
    ["monthly-profit-chart", { textContent: "Preparando" }],
  ]);
  const metrics = fs.readFileSync("frontend/static/scripts/pages/executive/sections/metrics.js", "utf8")
    .replace(/^import .*;\r?$/gm, "").replace(/export /g, "");
  const context = vm.createContext({ document: { getElementById: id => nodes.get(id) || null } });
  vm.runInContext(metrics, context);
  context.finishLoading(new Set(["monthly-profit-state"]));
  assert.equal(nodes.get("monthly-profit-state").textContent, "No disponible");
  assert.match(nodes.get("monthly-profit-chart").textContent, /periodo de nuevo/);
});
