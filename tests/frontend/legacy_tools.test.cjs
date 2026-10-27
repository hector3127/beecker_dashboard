const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const frozen = JSON.parse(
  fs.readFileSync(path.join(__dirname, "frozen/project_startup.json"), "utf8"),
);
function element(tag) {
  const node = {
    tagName: tag.toUpperCase(),
    children: [],
    style: {},
    dataset: {},
    className: "",
    isConnected: true,
    append(...items) {
      this.children.push(...items);
    },
    replaceChildren(...items) {
      this.children = [...items];
      this._text = undefined;
    },
    setAttribute(key, value) {
      if (key === "value") this._value = String(value);
      else this[key] = String(value);
    },
    addEventListener(name, handler) {
      this["on" + name] = handler;
    },
    classList: { remove() {}, toggle() {} },
  };
  Object.defineProperties(node, {
    textContent: {
      get() {
        return (
          this._text ??
          this.children
            .map((x) => (typeof x === "string" ? x : x.textContent))
            .join("")
        );
      },
      set(value) {
        this._text = String(value);
        this.children = [];
      },
    },
    value: {
      get() {
        return (
          this._value ??
          (this.tagName === "OPTION"
            ? this.textContent
            : this.options[0]?.value || "")
        );
      },
      set(value) {
        this._value = String(value);
      },
    },
    options: {
      get() {
        return this.children.filter((x) => x?.tagName === "OPTION");
      },
    },
    selectedOptions: {
      get() {
        return this.options.filter((x) => x.value === this.value);
      },
    },
    selectedIndex: {
      set(index) {
        this._value = this.options[index]?.value || "";
      },
    },
  });
  return node;
}
function setup(search = "", seed = null, id = "") {
  const requests = [],
    pending = {};
  const project = element("select");
  project.value = id || "Todos los proyectos";
  const option = element("option");
  option.value = project.value;
  option.textContent = project.value;
  project.append(option);
  const client = element("select"),
    clientOption = element("option");
  clientOption.textContent = "Todos los clientes";
  client.append(clientOption);
  const detail = element("section"),
    container = element("main");
  const nodes = {
    "f-proyecto": project,
    "f-cliente": client,
    "btn-refresh": {},
    "dashboard-general": element("section"),
    "dashboard-proyecto-detalle": detail,
    "view-container": container,
    "tpl-dashboard": { content: { cloneNode: () => element("section") } },
  };
  if (seed) nodes["project-context"] = { textContent: JSON.stringify(seed) };
  const document = {
    getElementById: (key) => nodes[key] || null,
    createElement: element,
    body: element("body"),
  };
  const scope = {
    URLSearchParams,
    document,
    window: { location: { search } },
    console,
  };
  vm.createContext(scope);
  const section = (file) =>
    fs.readFileSync(
      path.resolve(
        "frontend/static/scripts/pages/project_detail/sections",
        file,
      ),
      "utf8",
    );
  vm.runInContext(
    fs
      .readFileSync("frontend/static/scripts/lib/dom.js", "utf8")
      .replaceAll("export ", ""),
    scope,
  );
  vm.runInContext(
    section("project_entry_model.js").replaceAll("export ", ""),
    scope,
  );
  vm.runInContext(
    section("project_entry_view.js")
      .replace(/^import.*;$/gm, "")
      .replaceAll("export ", "") +
      "\nglobalThis.view={populate,selectProject,selectAccount,loading,failure,serverError};",
    scope,
  );
  vm.runInContext(
    section("project_entry.js")
      .replace(/^import.*;$/gm, "")
      .replaceAll("export ", ""),
    scope,
  );
  const api = {
    filters() {
      requests.push({ kind: "filters" });
      return new Promise((resolve) => {
        pending.filters = resolve;
      });
    },
    dashboard(pid, aer) {
      requests.push({ kind: aer ? "aer" : "executive", pid });
      return new Promise((resolve) => {
        pending.dashboard = resolve;
      });
    },
  };
  const controller = scope.createProjectEntry(api);
  let metadata = {};
  const env = {
    metadata: (...args) => (args.length ? (metadata = args[0]) : metadata),
    invalidatePrevious() {},
    previousLoad() {},
    clientChanged() {},
    render: { aer() {}, ixs() {}, executive() {} },
  };
  return { controller, env, requests, pending, detail, container, project };
}
const plain = (value) => JSON.parse(JSON.stringify(value));
function containsTag(node, tag) {
  return (
    node.tagName === tag ||
    node.children?.some(
      (child) => typeof child !== "string" && containsTag(child, tag),
    )
  );
}
test("entering the panel without a project makes no executive or filters requests", async () => {
  const value = setup(frozen.empty.search);
  await value.controller.start(value.env);
  assert.deepEqual(value.requests, frozen.empty.requests);
  assert.equal(value.detail.children.length, 0);
});
test("direct project and account links still initialize their filters", () => {
  assert.equal(frozen.direct.length, 2);
  for (const { search, requests } of frozen.direct) {
    const value = setup(search);
    void value.controller.start(value.env);
    assert.deepEqual(
      value.requests.map((x) => x.kind),
      requests,
    );
    assert.equal(value.detail.children.length, 0);
  }
});
test("a TYM direct link uses the AER/T&M endpoint even without filter metadata", () => {
  const value = setup("", null, frozen.tym.id);
  void value.controller.load(value.env);
  assert.deepEqual(
    value.requests.map((x) => x.pid),
    frozen.tym.requests,
  );
  assert.equal(value.requests[0].kind, "aer");
  assert.deepEqual(
    {
      head: value.detail.children[0].className.includes("legacy-project-head"),
      consulting: value.detail.textContent.includes("Consultando"),
      noSelect: !containsTag(value.detail, "SELECT"),
    },
    frozen.tym.loading,
  );
});
test("the full project entry boots from a portal URL with its ID in JSON", async () => {
  assert.equal(frozen.boot.length, 2);
  for (const { id, service, requests, head } of frozen.boot) {
    const value = setup("", { id }, id);
    void value.controller.mount(value.env);
    assert.equal(value.container.children.length, 1);
    assert.equal(value.requests[0]?.kind, "filters");
    value.pending.filters({
      proyectos: [{ id, nombre: "Proyecto", servicio: service }],
      clientes: ["Todos los clientes"],
    });
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(plain(value.requests), requests);
    assert.equal(value.project.value, id);
    assert.equal(
      value.detail.children[0].className.includes("legacy-project-head"),
      head,
    );
  }
});
