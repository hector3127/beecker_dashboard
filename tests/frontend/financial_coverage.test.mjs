import test from "node:test";
import assert from "node:assert/strict";
import {costCoverage, verifiedCostBlockers} from "../../frontend/static/scripts/pages/executive/sections/financial_model.js";

test("coverage distinguishes unavailable costs from valid zero and excludes future projects", () => {
  assert.deepEqual(costCoverage([
    {complete:true,cost:0}, {complete:false,cost:0}, {complete:false,cost:null}, {future:true,cost:null,complete:false},
  ]), {total:3,complete:1,partial:1,missing:1,future:1});
  assert.deepEqual(costCoverage([]), {total:0,complete:0,partial:0,missing:0,future:0});
});

test("alerts wait for prepared costs and omit projects with no verified result", () => {
  const partial = {cost: 0, complete: false};
  const failed = {cost: null, complete: false, error: "Sin vínculo"};
  const projects = [
    {cost: null, complete: false},
    {cost: 0, complete: true},
    {cost: null, complete: false, future: true},
    partial,
    failed,
  ];
  assert.deepEqual(verifiedCostBlockers(projects, null), []);
  assert.deepEqual(verifiedCostBlockers(projects, "2026-11-17T22:49:42"), [partial, failed]);
});
