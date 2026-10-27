const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const domState = require("./dom_state.cjs");
const frozen = JSON.parse(
  fs.readFileSync(path.join(__dirname, "frozen/portal_auxiliary.json"), "utf8"),
).loading;
const scope = { module: { exports: {} } };
vm.runInNewContext(
  fs
    .readFileSync("frontend/static/scripts/ui/portal-loading.js", "utf8")
    .replaceAll("export ", "") +
    "\nmodule.exports={isLoadingMessage,begin:beginLoading,inspect};",
  scope,
);
const { isLoadingMessage, begin, inspect } = scope.module.exports;
test("loading distinguishes an in-flight query from missing business data", () => {
  assert.equal(frozen.messages.length, 10);
  for (const { value, expected } of frozen.messages)
    assert.equal(isLoadingMessage(value), expected, value);
});
test("overlapping queries retain the loading marker until the last one ends", () => {
  const target = domState(),
    first = begin(target),
    second = begin(target),
    observed = [];
  const record = () =>
    observed.push({
      busy: target.getAttribute("aria-busy"),
      region: target.classList.contains("portal-loading-region"),
    });
  record();
  first();
  record();
  first();
  record();
  second();
  record();
  assert.deepEqual(observed, frozen.overlap);
});
test("rendered text loses its skeleton when a result or missing value arrives", () => {
  const target = {
    ...domState(),
    matches() {
      return true;
    },
    closest() {
      return null;
    },
    childElementCount: 0,
    textContent: "Consultando…",
  };
  inspect(target);
  const actual = [target.classList.contains("portal-loading-message")];
  target.textContent = "Pendiente";
  inspect(target);
  actual.push(target.classList.contains("portal-loading-message"));
  assert.deepEqual(actual, frozen.skeleton);
});
