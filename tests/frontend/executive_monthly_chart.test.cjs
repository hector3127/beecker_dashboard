const {test}=require('node:test');
const assert=require('node:assert/strict');
const {executiveMonthlyChartSvg}=require('../../apps/portal/static/portal/js/executive_monthly_chart.js');

test('six months fit a narrow card without a forced desktop width',()=>{
  const data={months:Array.from({length:6},(_,i)=>({month:'2026-0'+(i+1),revenue:100,cost:50,margin:50}))};
  const svg=executiveMonthlyChartSvg(data,300);
  assert.match(svg,/viewBox="0 0 300 275"/);
  assert.doesNotMatch(svg,/min-width:800/);
  assert.equal((svg.match(/<rect /g)||[]).length,12);
  assert.doesNotMatch(svg,/NaN|Infinity/);
  assert.match(executiveMonthlyChartSvg(data,250),/viewBox="0 0 250 275"/);
});

test('missing costs stay pending, missing margins split the line and negative values remain visible',()=>{
  const data={months:[
    {month:'2026-01',revenue:100,cost:120,margin:-20},
    {month:'2026-02',revenue:100,cost:null,margin:null},
    {month:'2026-03',revenue:-20,cost:0,margin:150},
  ]};
  const svg=executiveMonthlyChartSvg(data,900);
  assert.match(svg,/Pendiente/);
  assert.equal((svg.match(/<polyline /g)||[]).length,2);
  assert.match(svg,/-20/);
  assert.match(svg,/150/);
  assert.doesNotMatch(svg,/NaN|Infinity/);
});

test('long ranges retain readable spacing and empty ranges explain their state',()=>{
  const months=Array.from({length:24},()=>({month:'2026-01',revenue:1,cost:0,margin:100}));
  assert.match(executiveMonthlyChartSvg({months},320),/min-width:2136px/);
  assert.match(executiveMonthlyChartSvg({months:[]},320),/Sin datos para este periodo/);
});

test('wide charts show margin labels and mark partial values explicitly',()=>{
  const months=[{month:'2026-01',revenue:100,cost:25,margin:75}];
  assert.match(executiveMonthlyChartSvg({months,complete:true},900),/>75%<\/text>/);
  assert.match(executiveMonthlyChartSvg({months,complete:false},900),/>75%\*<\/text>/);
});
