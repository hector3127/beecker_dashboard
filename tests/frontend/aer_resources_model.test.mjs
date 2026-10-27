import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  resourcesModel,
  category,
  categoryClass,
  dateKey,
} from "../../frontend/static/scripts/pages/project_detail/sections/aer_resources_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/aer_resources.json", import.meta.url),
    "utf8",
  ),
);
const plain = (x) => JSON.parse(JSON.stringify(x));
assert.equal(frozen.cases.length, 16);
for (const { label, dashboard, selected, expected } of frozen.cases) {
  test(`Resource summary matches original: ${label}/${selected}`, () => {
    const input = structuredClone(dashboard);
    assert.deepEqual(plain(resourcesModel(input, selected)), expected);
    assert.deepEqual(input, dashboard);
  });
}
test("Category boundaries and date sorting preserve original behavior", () => {
  assert.equal(frozen.categories.length, 14);
  for (const item of frozen.categories) {
    const value =
      item.input.kind === "undefined" ? undefined : item.input.value;
    assert.equal(category(value), item.category);
    assert.equal(categoryClass(value), item.className);
  }
  assert.deepEqual(
    frozen.dates.map((x) => x.timezone),
    ["UTC", "America/Mexico_City"],
  );
  const before = process.env.TZ;
  try {
    for (const { timezone, cases } of frozen.dates) {
      process.env.TZ = timezone;
      assert.equal(cases.length, 7);
      for (const { input, expected } of cases)
        assert.equal(dateKey(input), expected);
    }
  } finally {
    if (before === undefined) delete process.env.TZ;
    else process.env.TZ = before;
  }
});
