import test from 'node:test';
import assert from 'node:assert/strict';
import { capacityState } from '../../frontend/static/scripts/pages/operativa/capacity_state.js';
const ready = { month: '2026-11', available: 2400 };
test('retains completed capacity while same month refresh loads or fails', () => {
  assert.equal(capacityState(ready, {month:'2026-11',loading:true},false).available,2400);
  assert.equal(capacityState(ready, {month:'2026-11',error:'source'},false).refresh_error,'source');
});
test('replaces fresh data and never retains another month or restricted data', () => {
  const fresh={month:'2026-11',available:2300};
  assert.equal(capacityState(ready,fresh,false),fresh);
  assert.equal(capacityState(ready,{month:'2026-12',loading:true},false).available,undefined);
  assert.equal(capacityState(ready,fresh,true),null);
  assert.equal(capacityState(ready,null,false),null);
});
