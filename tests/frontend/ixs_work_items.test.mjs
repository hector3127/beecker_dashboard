import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const modern = fs
  .readFileSync(
    "frontend/static/scripts/pages/project_detail/sections/ixs_work_item_actions.js",
    "utf8",
  )
  .replace(/import[^;]+;/, "")
  .replaceAll("export function", "function");
const original = fs
  .readFileSync("apps/portal/static/portal/js/proyecto_detalle.js", "utf8")
  .match(/  function _recalcularAvanceFilaWorkItem\([\s\S]*?\n  \}/)[0];
const context = {};
vm.runInNewContext(modern, context);
test("saved progress preserves the original equation and DOM input coercion", () => {
  for (const dev of [0, "", 60, "45.5", -10, 125, "invalid", null])
    for (const qa of [true, false]) {
      const cell = { innerHTML: "" };
      const row = {
        querySelector: (selector) =>
          selector.includes("5") ? { value: dev } : { checked: qa },
      };
      const old = {
        document: {
          getElementById: (id) => (id.startsWith("wi-row") ? row : cell),
        },
      };
      vm.runInNewContext(original, old);
      old._recalcularAvanceFilaWorkItem(101);
      const value = Number(
        cell.innerHTML.match(/progress-bar-fill[\s\S]*?width:([^%]+)%/)[1],
      );
      assert.equal(context.workItemProgress(dev, qa), value);
    }
});
