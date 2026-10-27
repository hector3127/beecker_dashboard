import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createProjectCompatibility } from "../../frontend/static/scripts/pages/project_detail/sections/project_compatibility.js";
import { createProjectScriptLoader } from "../../frontend/static/scripts/pages/project_detail/sections/project_script_loader.js";

function setup() {
  const scripts = [];
  const document = {
    createElement: () => ({
      dataset: {},
      remove() {
        this.removed = true;
      },
    }),
    head: { append: (script) => scripts.push(script) },
  };
  return { scripts, load: createProjectScriptLoader(document) };
}

test("concurrent and later bootstrap attempts evaluate each successful script once", async () => {
  const { scripts, load } = setup();
  const first = load("renderer.js", true),
    second = load("renderer.js", true);
  assert.equal(first, second);
  assert.equal(scripts.length, 1);
  assert.equal(scripts[0].dataset.projectBootstrap, "manual");
  scripts[0].onload();
  await first;
  await load("renderer.js", true);
  assert.equal(scripts.length, 1);
  const shim = load("shim.js");
  assert.equal(scripts[1].dataset.projectBootstrap, undefined);
  scripts[1].onload();
  await shim;
});

test("failed download is removed and can retry without reloading other successful scripts", async () => {
  const { scripts, load } = setup();
  const shim = load("shim.js");
  scripts[0].onload();
  await shim;
  const first = load("renderer.js", true);
  const failure = assert.rejects(
    first,
    /No se pudo cargar la interfaz del proyecto/,
  );
  scripts[1].onerror();
  await failure;
  assert.equal(scripts[1].removed, true);
  await load("shim.js");
  const retry = load("renderer.js", true);
  assert.equal(scripts.length, 3);
  scripts[2].onload();
  await retry;
});

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/project_script_loader.json", import.meta.url),
    "utf8",
  ),
);

test("compatibility bridge preserves account gate, cache rendering order and exact callbacks", () => {
  assert.equal(frozen.length, 4);
  for (const entry of frozen) {
    const calls = [],
      select = { value: "P" };
    const aer = entry.cached ? { aer: 1 } : null,
      ixs = entry.cached ? { ixs: 1 } : null;
    const executive = () => {};
    const previous = {
      start: () => calls.push(["start", true]),
      load: () => calls.push(["load", true]),
      account: () => entry.account,
      refresh: () => calls.push(["load"]),
      aer: () => aer,
      ixs: () => ixs,
      renderAer: (data) => calls.push(["aer", data]),
      renderIxs: (data) => calls.push(["ixs", data]),
      risks: () => calls.push(["risks"]),
      executive,
    };
    const bindings = createProjectCompatibility({
      getElementById: () => select,
    }).bindings(previous);
    bindings.previousStart();
    bindings.previousLoad();
    bindings.clientChanged();
    assert.deepEqual(calls, entry.calls);
    assert.equal(select.value, entry.selected);
    assert.deepEqual(Object.keys(bindings).sort(), entry.keys);
    assert.equal(bindings.executive === executive, entry.sameExecutive);
    assert.equal(bindings.previousStart, previous.start);
    assert.equal(bindings.previousLoad, previous.load);
  }
});
