// @ts-check
// Presentation only: contain wide tables without replacing rows or handlers.
/** Keep normalized model positions, but render labels/markers in CSS pixels.
 * @param {SVGSVGElement} chart
 */
export function fitEvaluationChart(chart) {
  const host = chart.parentElement;
  if (!host || !chart.isConnected) return;
  const width = host.clientWidth;
  const height = host.clientHeight;
  if (!width || !height) return;
  const points = (chart.dataset.evaluationPoints || '').trim().split(/\s+/)
    .map(pair => pair.split(',').map(Number));
  if (!points.length || points.some(point => point.length !== 2 || !point.every(Number.isFinite))) return;
  const scaled = points.map(([x, y]) => [x * width / 100, y * height / 100]);
  chart.setAttribute('viewBox', `0 0 ${width} ${height}`);
  chart.querySelector('polyline')?.setAttribute('points', scaled.map(point => point.join(',')).join(' '));
  chart.querySelectorAll('circle').forEach((circle, index) => {
    if (!scaled[index]) return;
    circle.setAttribute('cx', String(scaled[index][0]));
    circle.setAttribute('cy', String(scaled[index][1]));
    circle.setAttribute('r', '4');
  });
  chart.querySelectorAll('text').forEach((label, index) => {
    if (!scaled[index]) return;
    label.setAttribute('x', String(scaled[index][0]));
    label.setAttribute('y', String(Math.max(16, scaled[index][1] - 12)));
    label.setAttribute('font-size', '14');
  });
}

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
  table.classList.toggle('pd-dense-table', columns > 8);
  const firstLabel = table.tHead?.rows[0]?.cells[0]?.textContent?.trim() || '';
  table.classList.toggle('pd-id-first', ['#', 'ID', 'Id'].includes(firstLabel));
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
  document.body.dataset.projectDesign = 'delivery-v2';
  /** @type {Set<HTMLTableElement>} */
  const tables = new Set();
  /** @type {Set<SVGSVGElement>} */
  const charts = new Set();
  const resize = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(entries => {
    entries.forEach(entry => entry.target.querySelectorAll('svg[data-evaluation-points]')
      .forEach(chart => fitEvaluationChart(/** @type {SVGSVGElement} */ (chart))));
  });
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
    const root = document.getElementById('view-container');
    charts.forEach(chart => {
      if (chart.isConnected) return;
      if (chart.parentElement) resize?.unobserve(chart.parentElement);
      charts.delete(chart);
    });
    root?.querySelectorAll('svg[data-evaluation-points]').forEach(node => {
      const chart = /** @type {SVGSVGElement} */ (node);
      if (charts.has(chart)) return;
      charts.add(chart);
      if (chart.parentElement) resize?.observe(chart.parentElement);
      fitEvaluationChart(chart);
    });
    root?.querySelectorAll('.ixs-card,.aer-card,.ixai-card,.aeri-card,.aer-client-card,.bee-com-card').forEach(panel => {
      if (!panel.querySelector('h2,h3')) return;
      panel.classList.add('pd-panel');
      panel.querySelectorAll('h2,h3').forEach(heading => heading.classList.add('pd-panel-title'));
    });
    document.querySelectorAll('.ixs-nav,.aer-tabs').forEach(nav => {
      const active = nav.querySelector('button.active');
      if (root && active) root.dataset.projectSection = active.textContent?.trim().replace('✦ ', '') || '';
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
  return () => { observer.disconnect(); resize?.disconnect(); charts.clear(); };
}
