import { apiGet, apiSend } from '#app/data/api-client.js';
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
  const editor = el('section', {class: 'audit-editor', hidden: true});
  const add = el('button', {type: 'button', class: 'audit-primary', text: '+ Agregar registro', onclick: event => edit(null, 'project', event.currentTarget)});
  add.hidden = true;
  let changed = false;
  const status = el('p', {role: 'status', 'aria-live': 'polite'});
  const source = el('p', {class: 'audit-source'});
  const reconciliation = el('div', {class: 'audit-reconciliation'});
  const table = el('div', {class: 'audit-scroll', role: 'region', 'aria-label': 'Tabla del desglose', tabindex: '0'});
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
  let saving = false;
  let editorTrigger = null;
  const close = () => {if (!saving) dialog.close();};
  const retry = el('button', {type: 'button', text: 'Volver a consultar', onclick: load});
  const overview = el('div', {id: 'audit-overview', class: 'audit-overview', popover: 'auto',
    role: 'region', 'aria-label': 'Resumen y fuentes'},
    el('div', {class: 'audit-overview-heading'}, el('h3', {text: 'Resumen y fuentes'}),
      el('button', {type: 'button', popovertarget: 'audit-overview', popovertargetaction: 'hide', text: 'Cerrar resumen'})),
    source, reconciliation);
  const overviewButton = el('button', {type: 'button', popovertarget: 'audit-overview', text: 'Resumen y fuentes'});
  const toolbar = el('div', {class: 'audit-toolbar'},
    el('div', {class: 'audit-navigation'},
      el('div', {role: 'tablist', 'aria-label': 'Desglose de horas'}, ...tabs), add),
    el('div', {class: 'audit-controls'},
      el('label', {class: 'audit-month'}, el('span', {text: 'Mes'}), month),
      el('label', {class: 'audit-search'}, el('span', {text: 'Buscar en la tabla'}), search),
      el('div', {class: 'audit-tools'},
        el('button', {type: 'button', text: 'Limpiar filtros', onclick: () => {
          search.value = '';
          filters[active].clear();
          render();
        }}), retry, overviewButton)));
  const dialog = el('dialog', {class: 'specialty-audit', 'aria-labelledby': 'audit-title'},
    el('header', {class: 'audit-header'},
      el('div', {}, title, el('p', {text: 'Consulta y corrige la capacidad y las horas del mes.'})),
      el('button', {type: 'button', class: 'audit-close', 'aria-label': 'Cerrar modal', text: '×', onclick: close})),
    toolbar, panel, editor, overview,
    el('footer', {class: 'audit-footer'}, status, el('button', {type: 'button', text: 'Cerrar', onclick: close})),
  );
  function leaveEditor() {
    if (saving) return;
    editor.hidden = true;
    toolbar.hidden = false;
    panel.hidden = false;
    if (editorTrigger?.isConnected) editorTrigger.focus();
    else tabs[active].focus();
  }
  document.body.append(dialog);
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      const popup = dialog.querySelector(':popover-open');
      event.preventDefault(); event.stopPropagation();
      if (popup) {
        popup.hidePopover();
        if (popup === overview) overviewButton.focus({preventScroll: true});
        else dialog.querySelector('.audit-filter-trigger[aria-expanded="true"]')?.focus();
      } else if (!editor.hidden) leaveEditor();
      else close();
    }
  }, true);
  dialog.addEventListener('close', () => {sequence++; if (changed) location.reload(); else trigger.focus();});
  trigger.addEventListener('click', () => {dialog.showModal(); load();});
  month.addEventListener('change', load);
  search.addEventListener('input', render);

  function edit(row = null, kind = 'project', button = add) {
    const editingMonth = month.value;
    const target = row?.target;
    const capacity = kind === 'capacity';
    const history = row?.capacity_changes || [];
    const original = history[0]?.before;
    const canReset = capacity && history.length > 0 && original !== row.estimated;
    const originalLabel = original == null ? 'capacidad sin dato' : hours(original) + ' h';
    const person = el('input', {required: true, maxlength: 255, value: row?.name || ''});
    person.readOnly = capacity;
    const role = el('input', {required: true, maxlength: 80, value: row?.role || ''});
    const project = el('input', {required: true, maxlength: 255, value: row?.project || ''});
    const service = el('input', {required: true, maxlength: 80, value: row?.service || ''});
    const amount = el('input', {type: 'number', min: 0, max: 99999.9999, step: 0.0001, required: true,
      value: Number((capacity ? row?.estimated : row?.hours || 0)?.toFixed(4) || 0)});
    const billable = el('input', {type: 'checkbox', checked: target?.[4] ?? true});
    const message = el('p', {class: 'audit-editor-message', role: 'status'});
    const fields = el('div', {class: 'audit-editor-fields'},
      el('label', {class: 'audit-field-wide'}, 'Persona', person),
      ...(capacity ? [] : [
        el('label', {}, 'Rol', role),
        el('label', {class: 'audit-field-wide'}, 'Proyecto', project),
        el('label', {}, 'Servicio', service),
      ]),
      el('label', {}, 'Horas', amount),
      ...(capacity ? [] : [el('label', {class: 'audit-check'}, billable, 'Facturable')]),
    );
    const editorTitle = capacity ? 'Editar capacidad estimada' : target ? 'Editar registro agrupado' : 'Agregar registro';
    const controls = el('fieldset', {class: 'audit-editor-card'},
      el('legend', {text: editorTitle}),
      el('p', {class: 'audit-editor-month', text: 'Mes ' + editingMonth}),
      fields,
      ...(canReset ? [el('p', {class: 'audit-editor-month', text: 'Capacidad original: ' + originalLabel})] : []),
      message,
      el('div', {class: 'audit-editor-actions'},
        ...(target ? [el('button', {type: 'button', class: 'audit-danger', text: 'Eliminar', onclick: () => {
          if (window.confirm('¿Eliminar este grupo de horas de la facturabilidad del mes?')) save('delete');
        }})] : []),
        ...(canReset ? [el('button', {type: 'button', text: 'Restablecer capacidad', onclick: () => {
          if (window.confirm('¿Restablecer la capacidad original del mes (' + originalLabel + ')?')) {
            save('reset');
          }
        }})] : []),
        el('button', {type: 'button', text: 'Cancelar', onclick: leaveEditor}),
        el('button', {type: 'submit', class: 'audit-primary', text: 'Guardar'})),
    );
    const form = el('form', {onsubmit: event => {event.preventDefault(); save('save');}}, controls);
    editorTrigger = button;
    editor.replaceChildren(form);
    toolbar.hidden = true;
    panel.hidden = true;
    editor.hidden = false;
    (capacity ? amount : person).focus();

    async function save(action) {
      if (saving) return;
      saving = true;
      message.textContent = 'Guardando…';
      controls.disabled = true;
      month.disabled = true;
      const payload = {month: editingMonth, kind, action, person: person.value};
      if (target) payload.target = target;
      if (action === 'save') {
        payload.hours = amount.value;
        if (!capacity) Object.assign(payload, {
          role: role.value, project: project.value,
          service: service.value === 'Sin servicio asignado' ? 'NA' : service.value,
          billable: billable.checked,
        });
      }
      try {
        await apiSend('POST', 'screens/facturabilidad/correcciones/', payload);
        changed = true;
        if (dialog.open) {
          await load();
          tabs[active].focus();
        } else location.reload();
      } catch (error) {
        message.textContent = Object.values(error.fields || {}).flat().join(' ') || error.message;
      } finally {
        saving = false;
        controls.disabled = false;
        month.disabled = false;
      }
    }
  }

  function render() {
    tabs.forEach((tab, index) => {tab.setAttribute('aria-selected', String(active === index)); tab.tabIndex = active === index ? 0 : -1;});
    panel.setAttribute('aria-labelledby', `audit-tab-${active}`);
    dialog.querySelectorAll('.audit-filter-menu').forEach(menu => menu.remove());
    const horizontalOffset = table.scrollLeft;
    const verticalOffset = table.scrollTop;
    const sameTab = table.dataset.tab === String(active);
    table.dataset.tab = String(active);
    table.replaceChildren();
    reconciliation.replaceChildren();
    overviewButton.disabled = !data;
    if (!data) return;
    if (data.published_summary) {
      const published = data.published_summary;
      const estimates = data.people.reduce((sum, row) => sum + (row.estimated || 0), 0);
      const aer = data.people.reduce((sum, row) => sum + ((row.counted_services || row.billable_services || row.services).AER || 0) + (row.counted_services ? 0 : row.adjustment), 0);
      const reference = [
        ['Capacidad estimada', published.capacity, estimates],
        ['AER facturable + ajustes aprobados', published.fixed_hours, aer],
      ];
      const metrics = [
        ['Capacidad', published.capacity, ' h'],
        ['AER', published.fixed_hours, ' h'],
        ['Variables', published.variable_hours, ' h'],
        ['Libres', published.free_hours, ' h'],
        ['Facturabilidad global', published.global_percent, '%'],
      ];
      reconciliation.append(el('h4', {text: 'Resumen publicado'}),
        el('dl', {class: 'audit-metrics'}, ...metrics.map(([label, value, unit]) =>
          el('div', {}, el('dt', {text: label}), el('dd', {text: hours(value) + (value == null ? '' : unit)})))),
        el('div', {class: 'audit-comparison'}, el('table', {},
          el('thead', {}, el('tr', {}, ...['Concepto', 'Publicado', 'Detalle', 'Diferencia'].map(text => el('th', {scope: 'col', text})))),
          el('tbody', {}, ...reference.map(([label, approved, current]) => el('tr', {},
            ...[label, hours(approved), hours(current), hours(approved - current)].map(text => el('td', {text}))))))),
        el('p', {text: 'La comparación usa el mes completo. Los ajustes aprobados ya están incluidos en AER.'}));

    }
    const normalize = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const query = normalize(search.value);
    const serviceHours = row => row.counted_services || row.billable_services || row.services;
    const standardServices = ['AER', 'IXB', 'RAAS', 'SAAS', 'TYM'];
    const extraServices = [...new Set(data.people.flatMap(row => Object.keys(serviceHours(row))))]
      .filter(service => !standardServices.includes(service)).sort();
    const services = [...standardServices, ...extraServices];
    const labels = active
      ? ['Persona', 'Rol', 'Proyecto en GSE', 'Servicio asociado', 'Origen', 'Horas del registro o ajuste', 'Horas consideradas']
      : ['Persona', 'Rol', 'Estimadas (h)', 'Facturables consideradas (h)',
        ...services.map(service => service + ' facturable (h)'), 'Cambios de capacidad'];
    const numericFrom = active ? 5 : 2;
    const isNumeric = index => index >= numericFrom && (active || index < labels.length - 1);
    const display = (value, index) => isNumeric(index) ? hours(value) : value;
    const capacityHistory = row => row.capacity_changes?.length
      ? row.capacity_changes.map(({before, after, reset}) => `${hours(before)} → ${hours(after)} h${reset ? ' (restablecida)' : ''}`).join(' · ')
      : 'Sin cambios manuales';
    const records = active ? [...data.projects, ...(data.excluded || [])] : data.people;
    const all = (active ? [
      ...data.projects.map(row => [row.name, row.role, row.project, row.service, row.kind, row.hours, row.hours]),
      ...(data.excluded || []).map(row => [row.name, row.role, row.project, row.service, row.reason, row.hours, 0]),
    ] : data.people.map(row => [
      row.name, row.role, row.estimated, row.counted_hours ?? row.registered,
      ...services.map(service => serviceHours(row)[service] || 0), capacityHistory(row),
    ])).map((values, index) => ({values, record: records[index]}))
      .filter(({values: row, record}) => (!active && record.capacity_changes?.length)
        || row.slice(numericFrom).some(value => typeof value === 'number' && value !== 0));
    const rows = all.filter(({values: row}) => row.some(value => normalize(value).includes(query)) &&
      [...filters[active]].every(([index, selected]) => selected.has(String(row[index] ?? '—'))));
    const headings = labels.map((text, index) => {
      const options = [...new Set(all.map(({values: row}) => String(row[index] ?? '—')))];
      options.sort((a, b) => isNumeric(index) && a !== '—' && b !== '—' ? Number(a) - Number(b) : a.localeCompare(b, 'es'));
      const selected = filters[active].get(index);
      const draft = new Set(selected || options);
      const button = el('button', {type: 'button', class: 'audit-filter-trigger',
        'aria-label': `Filtrar ${text}`, 'aria-expanded': 'false',
        text: `${selected ? `${selected.size} seleccionados` : 'Todos'} ▾`});
      const optionList = el('div', {class: 'audit-filter-options'});
      const find = el('input', {type: 'search', placeholder: 'Buscar valor…', 'aria-label': `Buscar valores de ${text}`});
      const allCheckbox = el('input', {type: 'checkbox', 'aria-label': 'Seleccionar todos los valores visibles'});
      const syncSelection = visible => {
        allCheckbox.checked = visible.length > 0 && visible.every(value => draft.has(value));
        allCheckbox.indeterminate = visible.some(value => draft.has(value)) && !allCheckbox.checked;
      };
      const update = () => {
        const visible = options.filter(value => normalize(value).includes(normalize(find.value)) ||
          normalize(display(isNumeric(index) && value !== '—' ? Number(value) : value, index)).includes(normalize(find.value)));
        syncSelection(visible);
        optionList.replaceChildren(...visible.map(value => el('label', {}, el('input', {
          type: 'checkbox', checked: draft.has(value), value,
          onchange: event => {
          if (event.target.checked) draft.add(value); else draft.delete(value);
          syncSelection(visible);
        },
        }), el('span', {text: isNumeric(index) && value !== '—' ? hours(Number(value)) : value}))));
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
      menu.addEventListener('toggle', event => {
        button.setAttribute('aria-expanded', String(event.newState === 'open'));
      });
      button.addEventListener('click', () => {
        if (menu.matches(':popover-open')) {menu.hidePopover(); return;}
        draft.clear(); (filters[active].get(index) || options).forEach(value => draft.add(value));
        find.value = ''; update();
        const rect = button.getBoundingClientRect();
        menu.showPopover();
        const {width, height} = menu.getBoundingClientRect();
        menu.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - width - 8))}px`;
        const below = rect.bottom + 6;
        menu.style.top = `${below + height <= innerHeight - 8 ? below : Math.max(8, rect.top - height - 6)}px`;
        find.focus({preventScroll: true});
      });
      return el('th', {scope: 'col', class: isNumeric(index) ? 'audit-number' : ''}, el('span', {text}), button);
    });
    const body = el('tbody', {}, ...rows.map(({values: row, record}) => el('tr', {},
      ...row.map((value, index) => el('td', {class: isNumeric(index) ? 'audit-number' : '', text: display(value, index)})),
      ...(data.can_edit ? [el('td', {}, (!active || record.target) ? el('button', {
        type: 'button', text: active ? 'Editar registro' : 'Editar capacidad',
        class: 'audit-row-action',
        onclick: event => edit(record, active ? 'project' : 'capacity', event.currentTarget),
      }) : '—')] : []))));
    if (!rows.length) body.append(el('tr', {}, el('td', {colspan: labels.length + Number(Boolean(data.can_edit)), class: 'audit-empty', text: 'Sin coincidencias para este mes, áreas y búsqueda.'})));
    const totals = labels.map((_, index) => {
      if (index === 0) return el('th', {scope: 'row', text: 'Total filtrado'});
      if (!isNumeric(index)) return el('td');
      const known = rows.map(({values: row}) => row[index]).filter(value => typeof value === 'number');
      const total = known.reduce((sum, value) => sum + value, 0);
      return el('td', {class: 'audit-number', text: known.length ? hours(total) : '—', title: known.length < rows.length ? 'Suma de valores disponibles; hay datos pendientes.' : 'Suma de las filas filtradas'});
    });
    table.append(el('table', {class: data.can_edit ? 'audit-editable' : ''}, el('thead', {}, el('tr', {}, ...headings, ...(data.can_edit ? [el('th', {scope: 'col', text: 'Acciones'})] : []))), body,
      el('tfoot', {}, el('tr', {}, ...totals, ...(data.can_edit ? [el('td')] : [])))));
    table.scrollLeft = sameTab ? horizontalOffset : 0;
    table.scrollTop = sameTab ? verticalOffset : 0;
    status.textContent = `${rows.length} de ${all.length} ${active ? 'registros' : 'personas'} · ${month.value}`;

  }

  async function load() {
    const current = ++sequence;
    filters.forEach(filter => filter.clear());
    editor.hidden = true;
    toolbar.hidden = false;
    panel.hidden = false;
    add.hidden = true;
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
      add.hidden = !data.can_edit;
      source.textContent = `Base Clockify sincronizada: ${new Date(data.synced_at).toLocaleString('es-MX')}. ` +
        (data.published_revision ? `Existe cierre publicado (revisión ${data.published_revision}: ${data.published_source}). El detalle se obtiene de los registros del mes.` : 'Mes sin cierre general publicado.');
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
