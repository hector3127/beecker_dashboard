// @ts-check
import { mountTableColumns } from '../eva/table_columns.js';
import { bindPeriodPicker } from '#app/ui/period-picker.js';

document.querySelectorAll('details.pf').forEach(picker => {
  bindPeriodPicker(/** @type {HTMLDetailsElement} */ (picker));
});

const table = document.querySelector('#resource-history');
if (table) {
  const rows = [...table.querySelectorAll('tbody tr[data-resource-row]')];
  const types = Object.fromEntries(
    [...table.tHead.rows[1].cells].slice(2).map((_, i) => [i + 2, 'number'])
  );
  const inactive = row => Boolean(row.querySelector('.resource-inactive'));
  const conditions = {0: [
    {value:'resource-all', label:'Incluir dados de baja (todos)',
      matches:() => true},
    {value:'resource-active', label:'Excluir dados de baja',
      matches:row => !inactive(row)},
    {value:'resource-inactive', label:'Solo dados de baja', matches:inactive},
  ]};
  mountTableColumns({table, rows, types, conditions,
    standalone:true, groupLabels:false});
}
