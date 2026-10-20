const {test}=require('node:test'),assert=require('node:assert/strict');
const {executiveMoney}=require('../../apps/portal/static/portal/js/executive_numbers.js');
test('USD suffix follows actual magnitude, including negative amounts and boundaries',()=>{
 for(const [value,expected] of [[999.99,'999'],[1000,'1K'],[999999,'999K'],[1000000,'1M'],[2634000,'2.63M'],[19632000,'19.63M'],[1000000000,'1B'],[-19632000,'-19.63M'],[0,'0'],[null,'Pendiente']])assert.equal(executiveMoney(value),expected);
});
