// @ts-check
// Presentation only: contain wide tables without replacing rows or handlers.
/** @param {HTMLTableElement} table */
export function enhanceProjectTable(table) {
  if (!table.isConnected) return;
  let wrapper = table.parentElement;
  if (!wrapper) return;
  if (!wrapper.classList.contains('pd-table-scroll')) {
    if (!wrapper.matches('.table-scroll,.table-wrap,.ixs-table-scroll,.aer-table-wrap,.tw')) {
      const scroll = document.createElement('div');
      wrapper.insertBefore(scroll, table);
      scroll.append(table);
      wrapper = scroll;
    }
    wrapper.classList.add('pd-table-scroll');
  }
  const head = table.tHead?.rows;
  const columns = head?.length
    ? Math.max(...Array.from(head, row => Array.from(row.cells).reduce((n, cell) => n + cell.colSpan, 0)))
    : table.rows[0]?.cells.length || 0;
  table.classList.toggle('pd-wide-table', columns > 4);
  table.classList.toggle('pd-selection-first', !!table.tHead?.querySelector('tr:first-child th:first-child input[type=checkbox]'));
  if (columns > 4) {
    wrapper.tabIndex = 0;
    wrapper.setAttribute('role', 'region');
    const card = table.closest('.ixs-card,.aer-card,.ixai-card,.aeri-card,.card');
    const title = card?.querySelector('h2,h3,h4')?.textContent?.trim();
    wrapper.setAttribute('aria-label', title ? `Tabla: ${title}` : 'Detalle del proyecto, tabla desplazable');
  }
}

/** Enhance current/lazy panels and body-level dialogs; never reads API data. */
export function mountProjectPresentation() {
  if (typeof MutationObserver === 'undefined' || !document.getElementById('view-container')) return;
  document.body.dataset.projectDesign = 'delivery-v1';
  /** @type {Set<HTMLTableElement>} */
  const tables = new Set();
  let scheduled = false;
  /** @param {Node} node */
  function collect(node) {
    if (!(node instanceof Element)) return;
    if (node.matches('table')) tables.add(/** @type {HTMLTableElement} */ (node));
    node.querySelectorAll('table').forEach(table => tables.add(table));
    const table = node.closest('table');
    if (table) tables.add(table);
  }
  function flush() {
    scheduled = false;
    tables.forEach(enhanceProjectTable);
    tables.clear();
    document.querySelectorAll('.ixs-nav,.aer-tabs').forEach(nav => {
      const active = nav.querySelector('button.active');
      nav.querySelectorAll('button').forEach(button => {
        button.setAttribute('aria-pressed', String(button === active));
      });
      if (!(nav instanceof HTMLElement) || !(active instanceof HTMLElement)) return;
      const bounds = nav.getBoundingClientRect();
      const item = active.getBoundingClientRect();
      if (item.left < bounds.left || item.right > bounds.right) {
        nav.scrollLeft += item.left - bounds.left - (bounds.width - item.width) / 2;
      }
    });
  }
  collect(document.body);
  flush();
  const observer = new MutationObserver(records => {
    for (const record of records) {
      collect(record.target);
      record.addedNodes.forEach(collect);
    }
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(flush);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
  return () => observer.disconnect();
}
