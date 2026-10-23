// @ts-check
import { bindPeriodPicker } from '#app/ui/period-picker.js';

document.querySelectorAll('details.pf').forEach(picker => {
  bindPeriodPicker(/** @type {HTMLDetailsElement} */ (picker));
});
document.querySelectorAll('[data-columns]').forEach(element => {
  const bar = /** @type {HTMLElement} */ (element);
  bar.style.gridTemplateColumns = `repeat(${Number(bar.dataset.columns)},1fr)`;
});
document.querySelectorAll('[data-height]').forEach(element => {
  const bar = /** @type {HTMLElement} */ (element);
  bar.style.height = `${Number(bar.dataset.height)}%`;
});
