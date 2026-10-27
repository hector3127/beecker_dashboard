import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  filterWorkItems,
  workItemOptions,
  requirement,
  titleOnly,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_azure_table_model.js";

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/ixs_azure_table.json", import.meta.url),
    "utf8",
  ),
);
const same = (a, b) => assert.equal(JSON.stringify(a), JSON.stringify(b));
test("filters match original exact selectors and combined case-insensitive search", () => {
  assert.equal(frozen.rows.length, 4);
  assert.equal(frozen.filters.length, 8);
  for (const { input, expected } of frozen.filters) {
    const rows = structuredClone(frozen.rows),
      filters = structuredClone(input);
    same(filterWorkItems(rows, filters), expected);
    assert.deepEqual(rows, frozen.rows);
    assert.deepEqual(filters, input);
  }
});
test("options, requirements and displayed titles keep the original parsing", () => {
  assert.equal(frozen.options.length, 3);
  assert.equal(frozen.titles.length, 8);
  for (const { key, expected } of frozen.options)
    same(workItemOptions(frozen.rows, key), expected);
  for (const item of frozen.titles) {
    assert.equal(requirement(item.input), item.requirement);
    assert.equal(titleOnly(item.input), item.title);
  }
});
