/* Compare every account in the prepared cut; never rank only the old top five. */
(() => {
 'use strict';
 const keys = ['gross_profit', 'revenue', 'margin'];
 const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
 const numeric = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
 function rankAccounts(accounts, key, search = '', directions = {}) {
  if (!keys.includes(key)) key = 'gross_profit';
  const matches = accounts.filter(account => normalize(account.name).includes(normalize(search)));
  const eligible = matches.filter(account => numeric(account[key]));
  const compare = (a, b, direction) => (Number(a[key]) - Number(b[key])) * (direction === 'ascending' ? 1 : -1)
   || String(a.name).localeCompare(String(b.name), 'es');
  const ranked = [...eligible].sort((a, b) => compare(a, b, 'descending'));
  const split = Math.ceil(ranked.length / 2);
  const groups = {healthy: ranked.slice(0, split), unhealthy: ranked.slice(split)};
  const result = {missing: matches.length - eligible.length, matched: matches.length, eligible: eligible.length};
  for (const kind of ['healthy', 'unhealthy']) {
   const group = groups[kind];
   result[kind] = {
    count: group.length,
    rows: [...group].sort((a, b) => compare(a, b, directions[kind] || (kind === 'healthy' ? 'descending' : 'ascending'))).slice(0, 5)
   };
  }
  return result;
 }
 if (typeof module !== 'undefined' && module.exports) module.exports = {rankAccounts};
 if (typeof document === 'undefined') return;
 const controls = document.getElementById('account-ranking-controls');
 if (!controls) return;
 let snapshot;
 try { snapshot = JSON.parse(document.getElementById('financial-cache')?.textContent || '{}'); } catch (_) { snapshot = {}; }
 const accounts = snapshot.accounts?.accounts;
 const search = document.getElementById('ranking-search'), select = document.getElementById('ranking-sort');
 const status = document.getElementById('ranking-coverage');
 if (!Array.isArray(accounts)) {
  search.disabled = true; select.disabled = true;
  document.querySelectorAll('[data-sort-key]').forEach(button => { button.disabled = true; });
  for (const kind of ['healthy', 'unhealthy']) {
   document.getElementById(kind + '-account-count').textContent = 'Pendiente';
   document.getElementById(kind + '-financial-accounts').innerHTML = '<tr><td colspan="5">Listado completo de cuentas pendiente de preparar.</td></tr>';
  }
  status.textContent = 'El listado completo de cuentas está pendiente de preparar. Actualiza los datos para habilitar la comparación.';
  return;
 }
 const labels = {gross_profit: 'utilidad bruta', revenue: 'facturación', margin: 'margen bruto'};
 const defaults = () => ({healthy: 'descending', unhealthy: 'ascending'});
 let directions = defaults();
 const saved = new URLSearchParams(location.search);
 search.value = saved.get('ranking_buscar') || '';
 if (keys.includes(saved.get('ranking_criterio'))) select.value = saved.get('ranking_criterio');
 for (const kind of ['healthy', 'unhealthy']) {
  const direction = saved.get('ranking_' + kind);
  if (['ascending', 'descending'].includes(direction)) directions[kind] = direction;
 }
 const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[character]));
 const url = value => {
  try { const target = new URL(value, location.href); return target.origin === location.origin ? target.href : '#'; } catch (_) { return '#'; }
 };
 function draw() {
  const result = rankAccounts(accounts, select.value, search.value, directions);
  for (const kind of ['healthy', 'unhealthy']) {
   const group = result[kind], body = document.getElementById(kind + '-financial-accounts');
   document.getElementById(kind + '-account-count').textContent = group.rows.length + ' de ' + group.count + ' cuentas';
   body.innerHTML = group.rows.map((account, index) => {
    const partial = account.pending || account.partial ? '*' : '';
    const margin = numeric(account.margin) ? Number(account.margin).toLocaleString('es-MX', {maximumFractionDigits: 2}) + '%' + partial : 'No aplica';
    return '<tr><td>' + (index + 1) + '</td><td><a class="ranking-account" href="' + escape(url(account.url)) + '">' + escape(account.name) + '</a><small>' + escape(account.projects ?? 0) + ' proyectos' + (partial ? ' · Parcial*' : '') + '</small></td><td class="ranking-revenue">' + executiveMoney(account.revenue) + '</td><td class="ranking-margin"><strong>' + executiveMoney(account.gross_profit) + partial + '</strong></td><td class="ranking-margin"><b>' + margin + '</b></td></tr>';
   }).join('') || '<tr><td colspan="5">No hay cuentas con datos para este grupo y búsqueda.</td></tr>';
   const table = body.closest('table');
   table.querySelectorAll('[data-ranking-column]').forEach(header => {
    const active = header.dataset.rankingColumn === select.value;
    if (active) header.setAttribute('aria-sort', directions[kind]); else header.removeAttribute('aria-sort');
    header.querySelector('[data-sort-indicator]').textContent = active ? (directions[kind] === 'ascending' ? '↑' : '↓') : '↕';
   });
  }
  const partial = accounts.filter(account => normalize(account.name).includes(normalize(search.value)) && numeric(account[select.value]) && (account.pending || account.partial)).length;
  status.textContent = result.eligible + (result.eligible === 1 ? ' cuenta comparada por ' : ' cuentas comparadas por ') + labels[select.value] + '. '
   + (result.missing ? result.missing + ' sin dato para este criterio. ' : '')
   + (partial ? partial + (partial === 1 ? ' cuenta con costos parciales (*).' : ' cuentas con costos parciales (*).') : 'Sin ponderación 70/30.');
  const current = new URL(location.href);
  for (const [key, value] of [
   ['ranking_buscar', search.value],
   ['ranking_criterio', select.value === 'gross_profit' ? '' : select.value],
   ...['healthy', 'unhealthy'].map(kind => ['ranking_' + kind, directions[kind] === defaults()[kind] ? '' : directions[kind]])
  ]) {
   if (value) current.searchParams.set(key, value); else current.searchParams.delete(key);
  }
  history.replaceState(history.state, '', current.pathname + current.search + current.hash);
 }
 search.addEventListener('input', draw);
 select.addEventListener('change', () => { directions = defaults(); draw(); });
 document.querySelectorAll('[data-sort-key]').forEach(button => button.addEventListener('click', () => {
  const kind = button.dataset.rankingGroup, key = button.dataset.sortKey;
  if (select.value === key) directions[kind] = directions[kind] === 'ascending' ? 'descending' : 'ascending';
  else { select.value = key; directions = defaults(); }
  draw();
 }));
 draw();
})();
