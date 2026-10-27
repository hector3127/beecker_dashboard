const { test } = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");
const domState = require("./dom_state.cjs");
const frozen = JSON.parse(
  fs.readFileSync(path.join(__dirname, "frozen/portal_auxiliary.json"), "utf8"),
).navigation;
const source = fs
  .readFileSync("frontend/static/scripts/ui/return-links.js", "utf8")
  .replaceAll("export ", "");
function run(href, target, back = false) {
  const location = new URL(href),
    listeners = {};
  const link = {
    href: target,
    hasAttribute: (key) => back && key === "data-portal-back",
    classList: { contains: () => false },
  };
  vm.runInNewContext(source, {
    URL,
    URLSearchParams,
    location,
    document: {
      addEventListener: (name, fn) => (listeners[name] = fn),
      getElementById: () => null,
    },
  });
  listeners.click({ target: { closest: () => link } });
  const expected = frozen.links.find(
    (item) =>
      item.href === href && item.target === target && item.back === back,
  );
  assert.ok(expected, "Recorded navigation scenario");
  assert.equal(link.href, expected.expected);
  return new URL(link.href);
}
test("list to costs preserves filters and period as immediate parent", () => {
  const parent =
    "http://localhost/ejecutiva/cuentas/?periodo=mes&anio=2026&mes=10&buscar=Heineken";
  const url = run(
    parent,
    "http://localhost/ejecutiva/costos/detalle/?nombre=Heineken",
  );
  assert.equal(
    url.searchParams.get("volver"),
    new URL(parent).pathname + new URL(parent).search,
  );
  assert.equal(url.searchParams.get("mes"), "10");
});
test("account to costs preserves the nested list return chain", () => {
  const parent =
    "http://localhost/cuenta/a/?nombre=A&volver=%2Fejecutiva%2Fcuentas%2F";
  const url = run(
    parent,
    "http://localhost/ejecutiva/costos/detalle/?nombre=A",
  );
  assert.equal(
    url.searchParams.get("volver"),
    new URL(parent).pathname + new URL(parent).search,
  );
});

test("account to opportunity comparison preserves the account and its return chain", () => {
  const parent =
    "http://localhost/cuenta/heineken-mexico/?nombre=Heineken+Mexico&volver=%2F&periodo=mes&anio=2026&mes=10";
  const url = run(
    parent,
    "http://localhost/ejecutiva/oportunidades/?nombre=Heineken+Mexico",
  );
  assert.equal(
    url.searchParams.get("volver"),
    new URL(parent).pathname + new URL(parent).search,
  );
  assert.equal(url.searchParams.get("nombre"), "Heineken Mexico");
  assert.equal(url.searchParams.get("mes"), "10");
});
test("return links and external links are never rewritten", () => {
  const target =
    "http://localhost/cuenta/a/?nombre=A&volver=%2Fejecutiva%2Fcuentas%2F";
  assert.equal(
    run("http://localhost/ejecutiva/costos/detalle/", target, true).href,
    target,
  );
  assert.equal(
    run("http://localhost/", "https://other.test/cuenta/a/").href,
    "https://other.test/cuenta/a/",
  );
});

test("account list restores search and classification and saves changes in its URL", () => {
  const entry = frozen.account,
    location = new URL(entry.href),
    elements = {};
  let saved;
  function node() {
    return {
      ...domState(),
      value: "",
      textContent: "",
      listeners: {},
      addEventListener(name, fn) {
        this.listeners[name] = fn;
      },
      replaceChildren(...children) {
        this.children = children;
      },
      focus() {},
    };
  }
  const scope = {
    URL,
    URLSearchParams,
    location,
    history: {
      state: null,
      replaceState: (state, title, url) => {
        saved = url;
      },
    },
    document: {
      querySelectorAll: () => [],
      addEventListener() {},
      getElementById: (id) => (elements[id] ||= node()),
    },
    watchLoadingMessages() {},
    el: () => ({}),
    addEventListener() {},
  };
  vm.createContext(scope);
  vm.runInContext(
    fs
      .readFileSync("frontend/static/scripts/lib/format.js", "utf8")
      .replaceAll("export ", ""),
    scope,
  );
  vm.runInContext(
    fs
      .readFileSync("frontend/static/scripts/data/url-state.js", "utf8")
      .replaceAll("export ", ""),
    scope,
  );
  vm.runInContext(
    fs
      .readFileSync(
        "frontend/static/scripts/pages/all_accounts/main.js",
        "utf8",
      )
      .replace(/^import.*;$/gm, ""),
    scope,
  );
  assert.equal(elements["account-search"].value, entry.restored.search);
  assert.equal(elements["account-filter"].value, entry.restored.classification);
  // The new controller draws directly rather than dispatching a synthetic input.
  assert.equal(elements["account-count"].textContent, "0 de 0 cuentas");
  elements["account-search"].value = entry.nextSearch;
  elements["account-search"].listeners.input();
  assert.equal(saved, entry.saved);
  const url = new URL(saved, location);
  assert.equal(url.searchParams.get("buscar"), entry.nextSearch);
  assert.equal(url.searchParams.get("anio"), "2026");
});
