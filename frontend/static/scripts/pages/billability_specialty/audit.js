import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';

const format = new Intl.NumberFormat('es-MX', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const hours = value => value == null ? '—' : format.format(value);

export function bindAudit() {
  const trigger = document.getElementById('specialty-audit-open');
  if (!trigger) return;
  const months = JSON.parse(document.getElementById('specialty-audit-months')?.textContent || '[]');
  let data = null;
  let active = 0;
  let sequence = 0;
  const filters = [new Map(), new Map()];
  const title = el('h2', {id: 'audit-title', text: 'Personas y proyectos · Facturabilidad'});
  const month = el('select', {'aria-label': 'Mes del desglose'}, ...months.map(key => el('option', {value: key, text: key})));
  month.value = months.at(-1) || '';
  const search = el('input', {type: 'search', placeholder: 'Buscar persona, rol o proyecto', 'aria-label': 'Buscar en el desglose'});
  const status = el('p', {role: 'status', 'aria-live': 'polite'});
  const source = el('p', {class: 'audit-source'});
  const reconciliation = el('div', {class: 'audit-reconciliation'});
  const table = el('div', {class: 'audit-scroll', tabindex: '0'});
  const panel = el('section', {id: 'audit-panel', role: 'tabpanel', 'aria-labelledby': 'audit-tab-0'}, table);
  const tabs = ['Por persona', 'Detalle por proyecto'].map((text, index) => el('button', {
    type: 'button', role: 'tab', id: `audit-tab-${index}`, 'aria-controls': 'audit-panel',
    text, onclick: () => {active = index; render();},
    onkeydown: event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      active = event.key === 'Home' ? 0 : event.key === 'End' ? 1 : 1 - active;
      render(); tabs[active].focus();
    },
  }));
  const close = () => dialog.close();
  const retry = el('button', {type: 'button', text: 'Volver a consultar', onclick: load});
  const dialog = el('dialog', {class: 'specialty-audit', 'aria-labelledby': 'audit-title'},
    el('header', {}, title, el('button', {type: 'button', text: 'Cerrar ×', onclick: close})),
    el('p', {text: 'Consulta de solo lectura. Solo horas facturables incluidas por las reglas del resumen, sin Comida ni servicios excluidos. Los ajustes aprobados ya están incluidos en AER y en las horas consideradas; su columna es informativa y no debe sumarse otra vez. Se ocultan las filas con todas las horas en cero; — indica capacidad no disponible.'}),
    el('div', {class: 'audit-controls'}, el('label', {}, 'Mes ', month), search, el('button', {type: 'button', text: 'Limpiar filtros', onclick: () => {search.value = ''; filters[active].clear(); render();}}), retry),
    source, reconciliation, status, el('div', {role: 'tablist', 'aria-label': 'Desglose de horas'}, ...tabs), panel,
    el('footer', {}, el('span', {text: 'Esc para cerrar · Modifica los registros en su fuente de origen.'}), el('button', {type: 'button', text: 'Cerrar', onclick: close})),
  );
  document.body.append(dialog);
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      const popup = dialog.querySelector('.audit-filter-menu:popover-open');
      event.preventDefault(); event.stopPropagation();
      if (popup) popup.hidePopover(); else close();
    }
  }, true);
  dialog.addEventListener('close', () => {sequence++; trigger.focus();});
  trigger.addEventListener('click', () => {dialog.showModal(); load();});
  month.addEventListener('change', load);
  search.addEventListener('input', render);

  function render() {
    tabs.forEach((tab, index) => {tab.setAttribute('aria-selected', String(active === index)); tab.tabIndex = active === index ? 0 : -1;});
    panel.setAttribute('aria-labelledby', `audit-tab-${active}`);
    dialog.querySelectorAll('.audit-filter-menu').forEach(menu => menu.remove());
    table.replaceChildren();
    reconciliation.replaceChildren();
    if (!data) return;
    if (data.published_summary) {
      const published = data.published_summary;
      const estimates = data.people.reduce((sum, row) => sum + (row.estimated || 0), 0);
      const aer = data.people.reduce((sum, row) => sum + ((row.counted_services || row.billable_services || row.services).AER || 0) + (row.counted_services ? 0 : row.adjustment), 0);
      const reference = [
        ['Capacidad estimada', published.capacity, estimates],
        ['AER facturable + ajustes aprobados', published.fixed_hours, aer],
      ];
      reconciliation.append(el('h3', {text: 'Referencia del resumen publicado'}),
        el('p', {text: `Capacidad: ${hours(published.capacity)} h · AER: ${hours(published.fixed_hours)} h · Variables: ${hours(published.variable_hours)} h · Libres: ${hours(published.free_hours)} h · Global: ${hours(published.global_percent)}%`}),
        el('table', {}, el('thead', {}, el('tr', {}, ...['Concepto', 'Resumen publicado', 'Detalle actual', 'Diferencia por conciliar'].map(text => el('th', {text})))),
          el('tbody', {}, ...reference.map(([label, approved, current]) => el('tr', {},
            ...[label, hours(approved), hours(current), hours(approved - current)].map(text => el('td', {text})))))),
        el('p', {text: 'Estos totales son los del resumen. El cierre solo conserva cifras agregadas: el desglose actual no acredita el reparto histórico por persona. Esta comparación usa todas las filas del mes y áreas, independientemente de los filtros de la tabla.'}));
    }
    const normalize = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const query = normalize(search.value);
    const labels = active ? ['Persona', 'Rol', 'Proyecto en GSE', 'Servicio asociado', 'Origen', 'Horas registradas / ajuste'] :
      ['Persona', 'Rol', 'Estimadas (h)', 'Facturables consideradas (h)', 'AER facturable (h)', 'IXB facturable (h)', 'RaaS facturable (h)', 'SaaS facturable (h)', 'T&M facturable (h)', 'Otros facturables (h)', 'Ajustes incluidos (h)'];
    const values = row => active ? [row.name, row.role, row.project, row.service, row.kind, row.hours] :
      [row.name, row.role, row.estimated, row.counted_hours ?? row.registered, ...['AER', 'IXB', 'RAAS', 'SAAS', 'TYM'].map(key => (row.counted_services || row.billable_services || row.services)[key] || 0),
        Object.entries(row.counted_services || row.billable_services || row.services).reduce((sum, [key, value]) => sum + (['AER', 'IXB', 'RAAS', 'SAAS', 'TYM'].includes(key) ? 0 : value), 0), row.adjustment];
    const numericFrom = active ? 5 : 2;
    const display = (value, index) => index >= numericFrom ? hours(value) : value;
    const all = (active ? data.projects : data.people).map(values)
      .filter(row => row.slice(numericFrom).some(value => typeof value === 'number' && value !== 0));
    const rows = all.filter(row => row.some(value => normalize(value).includes(query)) &&
      [...filters[active]].every(([index, selected]) => selected.has(String(row[index] ?? '—'))));
    const headings = labels.map((text, index) => {
      const options = [...new Set(all.map(row => String(row[index] ?? '—')))];
      options.sort((a, b) => index >= numericFrom && a !== '—' && b !== '—' ? Number(a) - Number(b) : a.localeCompare(b, 'es'));
      const selected = filters[active].get(index);
      const draft = new Set(selected || options);
      const button = el('button', {type: 'button', class: 'audit-filter-trigger',
        'aria-label': `Filtrar ${text}`, 'aria-expanded': 'false',
        text: `${selected ? `${selected.size} seleccionados` : 'Todos'} ▾`});
      const optionList = el('div', {class: 'audit-filter-options'});
      const find = el('input', {type: 'search', placeholder: 'Buscar valor…', 'aria-label': `Buscar valores de ${text}`});
      const allCheckbox = el('input', {type: 'checkbox', 'aria-label': 'Seleccionar todos los valores visibles'});
      const update = () => {
        const visible = options.filter(value => normalize(value).includes(normalize(find.value)) ||
          normalize(display(index >= numericFrom && value !== '—' ? Number(value) : value, index)).includes(normalize(find.value)));
        allCheckbox.checked = visible.length > 0 && visible.every(value => draft.has(value));
        allCheckbox.indeterminate = visible.some(value => draft.has(value)) && !allCheckbox.checked;
        optionList.replaceChildren(...visible.map(value => el('label', {}, el('input', {
          type: 'checkbox', checked: draft.has(value), value,
          onchange: event => {if (event.target.checked) draft.add(value); else draft.delete(value); update();},
        }), el('span', {text: index >= numericFrom && value !== '—' ? hours(Number(value)) : value}))));
        if (!visible.length) optionList.append(el('p', {text: 'Sin coincidencias.'}));
      };
      find.addEventListener('input', update);
      allCheckbox.addEventListener('change', () => {
        const checked = allCheckbox.checked;
        optionList.querySelectorAll('input').forEach(input => {if (checked) draft.add(input.value); else draft.delete(input.value);});
        update();
      });
      const menu = el('div', {class: 'audit-filter-menu', popover: 'auto', role: 'group', 'aria-label': `Filtro de ${text}`},
        el('strong', {text}), find, el('label', {}, allCheckbox, 'Seleccionar todo'), optionList,
        el('div', {class: 'audit-filter-actions'},
          el('button', {type: 'button', text: 'Aceptar', onclick: () => {
            if (draft.size === options.length) filters[active].delete(index);
            else filters[active].set(index, new Set(draft));
            menu.hidePopover(); render();
            table.querySelectorAll('.audit-filter-trigger')[index]?.focus();
          }}),
          el('button', {type: 'button', text: 'Cancelar', onclick: () => {menu.hidePopover(); button.focus();}})));
      dialog.append(menu);
      menu.addEventListener('toggle', event => button.setAttribute('aria-expanded', String(event.newState === 'open')));
      button.addEventListener('click', () => {
        draft.clear(); (filters[active].get(index) || options).forEach(value => draft.add(value));
        find.value = ''; update();
        const rect = button.getBoundingClientRect();
        menu.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - 296))}px`;
        menu.style.top = `${Math.max(8, Math.min(rect.bottom + 4, innerHeight - 400))}px`;
        menu.showPopover(); find.focus();
      });
      return el('th', {scope: 'col'}, el('span', {text}), button);
    });
    const body = el('tbody', {}, ...rows.map(row => el('tr', {}, ...row.map((value, index) => el('td', {text: display(value, index)})))));
    if (!rows.length) body.append(el('tr', {}, el('td', {colspan: labels.length, text: 'Sin coincidencias para este mes, áreas y búsqueda.'})));
    const totals = labels.map((_, index) => {
      if (index === 0) return el('th', {scope: 'row', text: 'Total filtrado'});
      if (index < numericFrom) return el('td');
      const known = rows.map(row => row[index]).filter(value => typeof value === 'number');
      const total = known.reduce((sum, value) => sum + value, 0);
      return el('td', {text: known.length ? hours(total) : '—', title: known.length < rows.length ? 'Suma de valores disponibles; hay datos pendientes.' : 'Suma de las filas filtradas'});
    });
    table.append(el('table', {}, el('thead', {}, el('tr', {}, ...headings)), body,
      el('tfoot', {}, el('tr', {}, ...totals))));
    status.textContent = `${rows.length} de ${all.length} ${active ? 'registros agrupados por proyecto y servicio' : 'personas'} · ${month.value} · Totales de las filas visibles`;

  }

  async function load() {
    const current = ++sequence;
    filters.forEach(filter => filter.clear());
    data = null; render();
    status.textContent = 'Cargando desglose…';
    panel.setAttribute('aria-busy', 'true');
    source.textContent = '';
    const params = new URLSearchParams(location.search);
    try {
      const response = await apiGet('screens/facturabilidad/desglose/', {
        mes: month.value, roles: params.get('roles'), rol: params.getAll('rol'),
      });
      if (current !== sequence) return;
      if (!response.data.ok) throw new Error(response.data.error);
      data = response.data;
      source.textContent = `Base Clockify sincronizada: ${new Date(data.synced_at).toLocaleString('es-MX')}. ` +
        (data.published_revision ? `Existe cierre publicado (revisión ${data.published_revision}: ${data.published_source}). Este desglose consulta los registros actuales y puede diferir del cierre; no lo modifica.` : 'Mes sin cierre general publicado.');
      if (data.unmatched?.length) source.textContent += ` Personas sin coincidencia en Bandas/rol: ${data.unmatched.join(', ')}.`;
      render();
    } catch (error) {
      if (current === sequence) status.textContent = `No se pudo cargar: ${error.message || 'Intenta de nuevo.'}`;
    } finally {
      if (current === sequence) panel.setAttribute('aria-busy', 'false');
    }
  }
  render();
}
