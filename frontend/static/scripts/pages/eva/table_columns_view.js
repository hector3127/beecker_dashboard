// @ts-check
// view: eva/table_columns. Original data, ordering and interactions are preserved.
/**
 * @param {HTMLTableCellElement} cell
 */
export function cellText(cell) {
  const clone = cell.cloneNode(true);
  clone
    .querySelectorAll('button,[aria-hidden="true"]')
    .forEach((node) => node.remove());
  return clone.textContent.trim();
}
/**
 * @param {HTMLTableElement} table
 */
export function leafHeaders(table) {
  const grid = [];
  [...table.tHead.rows].forEach((row, r) => {
    grid[r] ||= [];
    let c = 0;
    [...row.cells].forEach((th) => {
      while (grid[r][c]) c++;
      for (let y = r; y < r + th.rowSpan; y++) {
        grid[y] ||= [];
        for (let x = c; x < c + th.colSpan; x++) grid[y][x] = th;
      }
      c += th.colSpan;
    });
  });
  return (grid.at(-1) || [])
    .map((th, index) => ({ th, index, group: grid[0][index] }))
    .filter((item) => item.th.colSpan === 1);
}
