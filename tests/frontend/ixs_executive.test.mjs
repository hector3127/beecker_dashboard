import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  executiveModel,
  timelineModel,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_executive_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/ixs_executive.json", import.meta.url),
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
const NativeDate = Date;
class FixedDate extends NativeDate {
  constructor(...args) {
    super(...(args.length ? args : [frozen.now]));
  }
  static now() {
    return +new NativeDate(frozen.now);
  }
}
function atFixedDate(callback) {
  try {
    globalThis.Date = FixedDate;
    inZones(callback);
  } finally {
    globalThis.Date = NativeDate;
  }
}

test("IXS executive preserves original thresholds, missing sources and presentation values", () => {
  atFixedDate((group) => {
    assert.equal(group.executive.length, 32);
    for (const { data, expected } of group.executive) {
      const before = plain(data);
      assert.deepEqual(plain(executiveModel(data)), expected);
      assert.deepEqual(data, before);
    }
  });
});
test("IXS timeline preserves phase matching, markers, suspensions and bounds", () => {
  atFixedDate((group) => {
    assert.equal(group.timeline.length, 10);
    for (const { data, expected, positions } of group.timeline) {
      const before = plain(data);
      const actual = timelineModel(data);
      assert.deepEqual(plain(actual), expected);
      if (actual) {
        assert.equal(positions.length, 3);
        for (const { date, expected: position } of positions)
          assert.equal(actual.pos(date), position);
      }
      assert.deepEqual(data, before);
    }
  });
});
