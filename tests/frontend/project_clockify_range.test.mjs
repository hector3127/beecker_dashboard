import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  createClockifyRange,
  rangeText,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_clockify_range.js";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const shortDate = vm.runInNewContext(
  "(" + source.match(/  function fmtFechaCorta\([\s\S]*?\n  \}/)[0] + ")",
);
const valid = {
  ok: true,
  fechaInicio: "2026-08-01",
  fechaFin: "2026-10-23T12:00:00",
};
const pending = () => {
  let resolve, reject;
  const promise = new Promise((a, b) => {
    resolve = a;
    reject = b;
  });
  return { promise, resolve, reject };
};

test("range presentation keeps original local dates and empty/error rules", () => {
  for (const result of [null, {}, { ok: false }, { ok: true, fechaFin: "x" }])
    assert.equal(rangeText(result), "");
  for (const result of [
    valid,
    { ...valid, fechaFin: null },
    { ...valid, fechaInicio: "invalid" },
  ]) {
    assert.equal(
      rangeText(result),
      `Clockify: ${shortDate(result.fechaInicio)} → ${shortDate(result.fechaFin)}`,
    );
  }
});

test("range loading clears failures and never reads without project/target", async () => {
  const node = { textContent: "" },
    response = pending(),
    ids = [];
  const controller = createClockifyRange(
    {
      clockifyRange(id) {
        ids.push(id);
        return response.promise;
      },
    },
    { getElementById: (id) => (id === "range" ? node : null) },
  );
  await controller.load("", "range");
  await controller.load("AER.001", "missing");
  assert.deepEqual(ids, []);
  const work = controller.load("CCO.001 | CR", "range");
  assert.equal(node.textContent, "Consultando rango…");
  assert.deepEqual(ids, ["CCO.001 | CR"]);
  response.reject(Error("source unavailable"));
  await work;
  assert.equal(node.textContent, "");
});

test("superseded responses and failures cannot overwrite newer range", async () => {
  const node = { textContent: "" },
    queue = [pending(), pending(), pending()];
  let index = 0;
  const controller = createClockifyRange(
    { clockifyRange: () => queue[index++].promise },
    { getElementById: () => node },
  );
  const first = controller.load("old", "range");
  const second = controller.load("old", "range");
  const third = controller.load("new", "range");
  queue[2].resolve(valid);
  await third;
  queue[0].resolve({ ...valid, fechaInicio: "2020-01-01" });
  queue[1].reject(Error("late failure"));
  await Promise.all([first, second]);
  assert.equal(node.textContent, rangeText(valid));
});

test("removed range node cannot update a replacement with the same ID", async () => {
  let target = { textContent: "" };
  const response = pending();
  const controller = createClockifyRange(
    { clockifyRange: () => response.promise },
    { getElementById: () => target },
  );
  const work = controller.load("old", "range");
  target = { textContent: "new project" };
  response.resolve(valid);
  await work;
  assert.equal(target.textContent, "new project");
});
