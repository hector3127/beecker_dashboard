import test from 'node:test';
import assert from 'node:assert/strict';
import { actionDistribution } from '../../frontend/static/scripts/pages/project_detail/sections/actions_distribution.js';
test('chart partitions overlapping source categories without duplicating actions',()=>{
 const rows=[{uid:'a',estado:'Pendiente'},{uid:'b',estado:'Detenido'},{uid:'c',estado:'Completado'},{uid:'d',estado:'En progreso'}];
 const result=actionDistribution({filas:rows,ac:{vencidas:[rows[0],rows[1],rows[2]]}});
 assert.deepEqual(result.map(x=>x.count),[1,1,1,1]);
 assert.equal(result.reduce((n,x)=>n+x.count,0),rows.length);
});
test('empty chart has zero categories and no invented records',()=>{
 assert.deepEqual(actionDistribution({filas:[],ac:{}}).map(x=>x.count),[0,0,0,0]);
});
