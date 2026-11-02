// Categories are disjoint for the chart; source KPI definitions stay intact.
export function actionDistribution(model) {
  const key = row => String(row.uid ?? [row.accion,row.responsable,row.fechaLimite].join('|'));
  const late = new Set((model.ac.vencidas || []).map(key));
  const buckets = [
    {label:'Abiertas sin vencer',count:0,color:'#7424f2'},
    {label:'Vencidas',count:0,color:'#ff557c'},
    {label:'Detenidas',count:0,color:'#ffbe3b'},
    {label:'Cerradas',count:0,color:'#b48cff'},
  ];
  for (const row of model.filas) {
    const state = String(row.estado || '').toLowerCase();
    const index = /complet|cerrad/.test(state) ? 3 : /detenid|paus|bloq/.test(state) ? 2 : late.has(key(row)) || /vencid/.test(state) ? 1 : 0;
    buckets[index].count++;
  }
  return buckets;
}
