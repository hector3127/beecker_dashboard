import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createEntryRuntime } from "../../frontend/static/scripts/pages/project_detail/sections/project_entry_runtime.js";
import { createProjectCompatibility } from "../../frontend/static/scripts/pages/project_detail/sections/project_compatibility.js";

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/project_compatibility.json", import.meta.url),
    "utf8",
  ),
);

function scenario(before, after, cached, hasSelect = true) {
  const calls = [],
    project = { value: "P" };
  let account = before;
  let aer = cached ? { aer: 1 } : null,
    ixs = cached ? { ixs: 1 } : null;
  const provider = {
    start: (...args) => {
      calls.push(["start", ...args]);
      return "started";
    },
    load: (...args) => {
      calls.push(["load", ...args]);
      return "loaded";
    },
    account: () => account,
    refresh: () => {
      calls.push(["refresh"]);
      account = after;
    },
    aer: () => aer,
    ixs: () => ixs,
    renderAer: (value) => {
      calls.push(["aer", value]);
    },
    renderIxs: (value) => {
      calls.push(["ixs", value]);
    },
    risks: () => calls.push(["risks"]),
    executive: () => {},
  };
  const doc = { getElementById: () => (hasSelect ? project : null) };
  const bindings = createProjectCompatibility(doc).bindings(provider);
  return {
    provider,
    bindings,
    calls,
    project,
    updateCache(value) {
      aer = value;
      ixs = value;
    },
  };
}

test("client contract preserves original order and account recheck after refresh", () => {
  assert.equal(frozen.length, 16);
  for (const { before, after, cached, selected, expected } of frozen) {
    const modern = scenario(before, after, cached, selected);
    modern.bindings.clientChanged();
    assert.deepEqual(modern.calls, expected.calls);
    assert.equal(modern.project.value, expected.selected);
  }
});

test("callbacks retain identity, arguments, result and synchronous invocation", () => {
  const s = scenario("", "", false);
  assert.equal(s.bindings.previousStart, s.provider.start);
  assert.equal(s.bindings.previousLoad, s.provider.load);
  assert.equal(s.bindings.executive, s.provider.executive);
  assert.equal(s.bindings.previousStart("a"), "started");
  assert.equal(s.bindings.previousLoad("b"), "loaded");
  assert.deepEqual(s.calls, [
    ["start", "a"],
    ["load", "b"],
  ]);
});

test("report caches are read at the time of change, not when bindings are built", () => {
  const s = scenario("", "", false),
    latest = { cut: "new" };
  s.updateCache(latest);
  s.bindings.clientChanged();
  assert.deepEqual(s.calls, [
    ["refresh"],
    ["aer", latest],
    ["ixs", latest],
    ["risks"],
  ]);
});

test("store-owned reports retain original account selection and refresh ordering", () => {
  for (const before of ["", " Todos los clientes ", "ACME"])
    for (const after of ["", "TODOS LOS CLIENTES", "OTHER"])
      for (const cached of [false, true]) {
        const calls = [],
          project = { value: "P" },
          client = { value: before };
        const state = { reportAer: null, reportIxs: null };
        const latest = cached ? { filas: [{ id: "current" }] } : null;
        const api = createProjectCompatibility({
          getElementById: (id) => (id === "f-cliente" ? client : project),
        });
        const bindings = api.reports(state, {
          refresh() {
            calls.push("refresh");
            client.value = after;
            state.reportAer = latest;
            state.reportIxs = latest;
          },
          renderAer: (value) => calls.push(["aer", value]),
          renderIxs: (value) => calls.push(["ixs", value]),
          risks: () => calls.push("risks"),
        });
        bindings.clientChanged();
        const account = (value) =>
          value.trim() && !/^todos los clientes$/i.test(value.trim());
        assert.equal(
          project.value,
          account(before) ? "Todos los proyectos" : "P",
        );
        assert.deepEqual(
          calls,
          account(after)
            ? ["refresh"]
            : [
                "refresh",
                ...(cached
                  ? [
                      ["aer", latest],
                      ["ixs", latest],
                    ]
                  : []),
                "risks",
              ],
        );
      }
});

test("store reports handle absent client and project selectors", () => {
  const calls = [];
  createProjectCompatibility({ getElementById: () => null })
    .reports(
      { reportAer: null, reportIxs: null },
      {
        refresh: () => calls.push("refresh"),
        risks: () => calls.push("risks"),
      },
    )
    .clientChanged();
  assert.deepEqual(calls, ["refresh", "risks"]);
});

test("real modern bridge starts through modular entry with a fresh context", () => {
  const calls = [];
  let version = 1;
  const runtime = createEntryRuntime({
    contexts: { entry: (callbacks) => ({ ...callbacks, version }) },
    entry: {
      startCompatibility: (env) => {
        calls.push(env);
        return "modular-start";
      },
    },
  });
  const bindings = runtime.context();
  version = 2;
  assert.equal(bindings.previousStart(), "modular-start");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].version, 2);
  assert.notEqual(calls[0], bindings);
});
