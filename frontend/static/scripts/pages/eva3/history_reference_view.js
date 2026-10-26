// @ts-check
// view: eva3/history_reference. Original data, ordering and interactions are preserved.
/**
 * @param {HTMLTableCellElement} cell
 */
export const text = (cell) => {
  const clone = cell.cloneNode(true);
  clone
    .querySelectorAll('button,[aria-hidden="true"]')
    .forEach((button) => button.remove());
  return clone.textContent.trim();
};
