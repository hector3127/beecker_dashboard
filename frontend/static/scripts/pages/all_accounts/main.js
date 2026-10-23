// @ts-check
// Todas las cuentas: busqueda, clasificacion, resumen y orden por columna.
// Las filas llegan en la plantilla; aqui solo el comportamiento.
import { formatCompact, plain } from '#app/lib/format.js';
import { watchLoadingMessages } from '#app/ui/portal-loading.js';

watchLoadingMessages();
/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const rows = /** @type {HTMLTableRowElement[]} */ ([...document.querySelectorAll('tr[data-name]')]);
const search = /** @type {HTMLInputElement} */ (byId('account-search'));
const filter = /** @type {HTMLSelectElement} */ (byId('account-filter'));
const body = byId('accounts-body');
const empty = byId('accounts-empty');

// Los importes se muestran con K, M o B.
document.querySelectorAll('[data-money]').forEach((node) => {
  const cell = /** @type {HTMLTableCellElement} */ (node);
  const partial = /** @type {HTMLElement} */ (cell.closest('tr')).dataset.partial === 'true' && cell.cellIndex !== 2;
  cell.textContent = formatCompact(Number(cell.dataset.money)) + (partial ? '*' : '');
});

function draw() {
  let count = 0;
  for (const row of rows) {
    row.hidden = !(plain(/** @type {string} */ (row.dataset.name)).includes(plain(search.value)) && (!filter.value || row.dataset.classification === filter.value));
    if (!row.hidden) count += 1;
  }
  byId('account-count').textContent = `${count} de ${rows.length} cuentas`;
  empty.hidden = count !== 0;
}

byId('summary-healthy').textContent = String(rows.filter((r) => r.dataset.classification === 'healthy').length);
byId('summary-pending').textContent = String(rows.filter((r) => r.dataset.classification === 'pending').length);
const complete = rows.filter((r) => r.dataset.classification !== 'pending' && r.dataset.classification !== 'future' && r.dataset.margin !== '');
byId('summary-margin').textContent = complete.length
  ? `${(complete.reduce((sum, r) => sum + Number(r.dataset.margin), 0) / complete.length).toLocaleString('es-MX', { maximumFractionDigits: 1 })}%`
  : '—';

document.querySelectorAll('th button').forEach((node, index) => {
  let ascending = true;
  node.addEventListener('click', () => {
    /** @param {HTMLTableRowElement} row */
    const value = (row) => {
      const cell = row.cells[index];
      if (index >= 2 && index <= 4) return Number(cell.dataset.money);
      if (index === 5) return row.dataset.margin === '' ? -Infinity : Number(row.dataset.margin);
      if (index === 1) return Number(cell.textContent);
      return (cell.textContent || '').trim();
    };
    rows.sort((a, b) => {
      const av = value(a);
      const bv = value(b);
      return (typeof av === 'number' ? av - /** @type {number} */ (bv) : String(av).localeCompare(String(bv), 'es')) * (ascending ? 1 : -1);
    });
    for (const row of rows) body.insertBefore(row, empty);
    document.querySelectorAll('th').forEach((th) => th.removeAttribute('aria-sort'));
    /** @type {HTMLElement} */ (node.parentElement).setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
    ascending = !ascending;
  });
});
search.addEventListener('input', draw);
filter.addEventListener('change', draw);
draw();
