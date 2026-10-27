import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { genericTimeline } from "../../frontend/static/scripts/pages/project_detail/sections/generic_timeline_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/generic_timeline.json", import.meta.url),
    "utf8",
  ),
);
const plain = (value) => JSON.parse(JSON.stringify(value));
function inZones(callback) {
  const previous = process.env.TZ;
  try {
    for (const zone of ["UTC", "America/Mexico_City"]) {
      process.env.TZ = zone;
      callback(frozen[zone]);
    }
  } finally {
    if (previous === undefined) delete process.env.TZ;
    else process.env.TZ = previous;
  }
}

const comparable = (model) =>
  plain({ ...model, states: model.filasReal.map(model.estadoEtapaReal) });
function check({ data, now, expected }) {
  const before = plain(data);
  assert.deepEqual(comparable(genericTimeline(data, now)), expected);
  assert.deepEqual(data, before, "the pure model must not mutate backend data");
}
test("generic rows, scale, markers and completion match the untouched fallback for all cuts/states", () => {
  inZones((group) => {
    assert.equal(group.cuts.length, 63);
    group.cuts.forEach(check);
  });
});
test("suspension boundaries, repeated phases, missing dates and marker categories retain their precedence", () => {
  inZones((group) => {
    assert.equal(group.boundaries.length, 16);
    group.boundaries.forEach(check);
  });
});
