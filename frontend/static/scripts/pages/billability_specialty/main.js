// @ts-check
import { bindPeriodPicker } from '#app/ui/period-picker.js';

document.querySelectorAll('details.pf').forEach(picker => {
  bindPeriodPicker(/** @type {HTMLDetailsElement} */ (picker));
});
