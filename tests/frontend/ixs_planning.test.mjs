import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  planningModel,
  planningSummary,
} from "../../frontend/static/scripts/pages/project_detail/sections/ixs_planning_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/ixs_planning.json", import.meta.url),
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

test("planning deadlines and vacations preserve the original date boundaries and states", () => {
  atFixedDate((group) => {
    assert.equal(group.summary.length, 5);
    for (const { plan, azure, expected } of group.summary) {
      const before = plain({ plan, azure });
      assert.deepEqual(plain(planningSummary(plan, azure)), expected);
      assert.deepEqual({ plan, azure }, before);
    }
  });
});
test("planning indicators, stage ranking and six-week distinct resources match the old renderer", () => {
  atFixedDate((group) => {
    assert.equal(group.model.length, 4);
    for (const { data, plan, azure, expected } of group.model) {
      const before = plain({ data, plan, azure });
      const { timeline, ...actual } = planningModel(data, plan, azure);
      assert.deepEqual(plain(actual), expected);
      assert.equal(
        timeline.hitosAdicionales.length,
        (data.hitosAdicionales || []).length + plan.compromisos.length,
      );
      assert.deepEqual({ data, plan, azure }, before);
    }
  });
});
