import assert from 'node:assert/strict';
import test from 'node:test';
import { selectProjects } from '../../frontend/static/scripts/pages/account_hours/selection.js';

const report = {
  months: [{key:'2026-01'},{key:'2026-02'}],
  projects: [
    {id:'A',known_hours:2,cells:[{hours:2,partial:false},{hours:null,partial:true}]},
    {id:'B',known_hours:5,cells:[{hours:1,partial:false},{hours:4,partial:false}]},
  ],
};
test('no selection keeps the complete report', () => {
  assert.equal(selectProjects(report,new Set()),report);
});
test('one project has its own totals and keeps unknown months', () => {
  const data = selectProjects(report,new Set(['A']));
  assert.equal(data.known_hours,2);
  assert.deepEqual(data.totals,[{hours:2,partial:false},{hours:null,partial:true}]);
  assert.equal(data.partial,true);
  assert.equal(report.projects.length,2);
});
test('several projects sum once and preserve partial data', () => {
  const data = selectProjects(report,new Set(['A','B']));
  assert.equal(data.known_hours,7);
  assert.deepEqual(data.totals,[{hours:3,partial:false},{hours:4,partial:true}]);
});
