// Temporary original-only capture; run explicitly from repository root.
import fs from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";
const captured = {};
const jobs = [];
const test = (_name, callback) => jobs.push(callback());
const source = fs.readFileSync(
  "tests/reference/static/portal/js/cached_page.js",
  "utf8",
);

function harness(ok) {
  const state = {
    textContent: "Último corte",
    appendChild(button) {
      this.button = button;
    },
  };
  const requests = [];
  let reloads = 0;
  vm.runInNewContext(source, {
    URL,
    document: { getElementById: () => state, createElement: () => ({}) },
    window: {
      location: {
        href: "http://localhost/comercial/?cliente=ACME",
        reload() {
          reloads++;
        },
      },
    },
    fetch: async (url) => {
      requests.push(url.toString());
      return { ok: true, text: async () => "<body>" };
    },
    DOMParser: class {
      parseFromString() {
        return { body: { dataset: { portalReady: ok ? "true" : "false" } } };
      }
    },
  });
  return { state, requests, reloads: () => reloads };
}

test("refresh prepares the new cut without resetting the visible page or filters", async () => {
  const h = harness(true);
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(h.requests[0], /cliente=ACME&actualizar=1/);
  assert.equal(h.reloads(), 0);
  assert.match(h.state.textContent, /Nuevo corte disponible/);
  captured.genericReady = {
    reloadsBefore: h.reloads(),
    message: h.state.textContent,
  };
  h.state.button.onclick();
  captured.genericReady.reloadsAfter = h.reloads();
  assert.equal(h.reloads(), 1);
});

test("failed source refresh keeps the old cut and offers a retry", async () => {
  const h = harness(false);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(h.reloads(), 0);
  assert.equal(h.state.button, undefined);
  assert.match(h.state.textContent, /Se conserva el último corte/);
  captured.genericFailure = {
    reloads: h.reloads(),
    message: h.state.textContent,
    offersApply: !!h.state.button,
  };
});

function executiveHarness(states) {
  const requests = [];
  let reloads = 0;
  const state = {
    dataset: { refreshUrl: "/ejecutiva/actualizacion/" },
    appendChild(button) {
      this.button = button;
    },
  };
  vm.runInNewContext(source, {
    URL,
    document: {
      getElementById: () => state,
      querySelector: () => ({ value: "csrf-token" }),
      createElement: () => ({}),
    },
    window: {
      location: {
        href: "http://localhost/?periodo=mes&anio=2026&mes=9",
        reload() {
          reloads++;
        },
      },
      addEventListener() {},
    },
    setTimeout: (callback) => callback(),
    fetch: async (url, options) => {
      requests.push({ url: String(url), options });
      return { ok: true, json: async () => states.shift() };
    },
  });
  return { state, requests, reloads: () => reloads };
}

test("executive refresh polls a light status endpoint and retains dates and CSRF", async () => {
  const h = executiveHarness([
    { state: "queued" },
    { state: "running" },
    { state: "ready", partial: false },
  ]);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(h.requests.length, 3);
  assert.match(
    h.requests[0].url,
    /actualizacion\/\?periodo=mes&anio=2026&mes=9/,
  );
  assert.equal(h.requests[0].options.method, "POST");
  assert.equal(h.requests[0].options.headers["X-CSRFToken"], "csrf-token");
  assert.equal(h.requests[1].options.cache, "no-store");
  captured.poll = {
    methods: h.requests.map((x) => x.options.method || "GET"),
    csrf: h.requests[0].options.headers["X-CSRFToken"],
    cache: h.requests[1].options.cache,
  };
  assert.equal(h.reloads(), 0);
  assert.match(h.state.textContent, /Nuevo corte disponible/);
  h.state.button.onclick();
  assert.equal(h.reloads(), 1);
});

test("executive partial and failed refreshes do not claim a complete cut", async () => {
  const partial = executiveHarness([{ state: "ready", partial: true }]);
  const failed = executiveHarness([{ state: "running" }, { state: "failed" }]);
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(partial.state.textContent, /corte parcial/);
  assert.ok(partial.state.button);
  assert.match(failed.state.textContent, /Se conserva el último corte/);
  assert.equal(failed.state.button, undefined);
  assert.equal(failed.reloads(), 0);
  captured.partial = {
    reloads: partial.reloads(),
    offersApply: !!partial.state.button,
    message: partial.state.textContent,
  };
  captured.failure = {
    reloads: failed.reloads(),
    offersApply: !!failed.state.button,
    message: failed.state.textContent,
  };
});

await Promise.all(jobs);
fs.writeFileSync(
  "tests/frontend/frozen/cached_page_previous.json",
  JSON.stringify(captured, null, 2) + "\n",
);
