import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  projectParams,
  metadata,
  family,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_entry_model.js";

const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/project_entry_families.json", import.meta.url),
    "utf8",
  ),
);
assert.equal(frozen.length, 9);
test("project route seed retains priority over query and keeps return filters", () => {
  const params = projectParams(
    "?proyecto=OTHER&volver=%2Fcuenta%2Foxxo%2F&cuenta=Oxxo",
    '{"id":"AER.001"}',
  );
  assert.equal(params.get("proyecto"), "AER.001");
  assert.equal(params.get("volver"), "/cuenta/oxxo/");
  assert.equal(params.get("cuenta"), "Oxxo");
  assert.equal(projectParams("?proyecto=IXB.001").get("proyecto"), "IXB.001");
});
test("metadata preserves original keys, references and last duplicate", () => {
  const first = { id: "1", servicio: "AER" },
    last = { id: "1", servicio: "IXB" };
  assert.deepEqual(metadata({}), {});
  assert.equal(metadata({ proyectos: [first, last] })["1"], last);
  assert.equal(metadata({ proyectos: [first] })["1"], first);
});
for (const { service, cases } of frozen) {
  test(`family matches original service rules: ${service || "missing"}`, () => {
    assert.equal(cases.length, 4);
    for (const { id, map, expected } of cases) {
      const input = structuredClone(map);
      assert.equal(family(id, input), expected);
      assert.deepEqual(input, map);
    }
  });
}
