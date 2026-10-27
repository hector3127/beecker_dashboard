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
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/ixs_work_items.json", import.meta.url),
    "utf8",
  ),
);
const context = {};
vm.runInNewContext(modern, context);
test("saved progress preserves the original equation and DOM input coercion", () => {
  assert.equal(frozen.length, 16);
  for (const { dev, qa, expected } of frozen)
    assert.equal(context.workItemProgress(dev, qa), expected);
});
