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
    el('p', {text: 'Consulta de solo lectura. Horas facturables y no facturables, sin Comida. Los ajustes aprobados se identifican por separado. Se incluyen personas con capacidad cero para revisar sus registros; — indica capacidad no disponible.'}),
    el('div', {class: 'audit-controls'}, el('label', {}, 'Mes ', month), search, el('button', {type: 'button', text: 'Limpiar filtros', onclick: () => {search.value = ''; filters[active].clear(); render();}}), retry),
    source, status, el('div', {role: 'tablist', 'aria-label': 'Desglose de horas'}, ...tabs), panel,
    el('footer', {}, el('span', {text: 'Esc para cerrar · Modifica los registros en su fuente de origen.'}), el('button', {type: 'button', text: 'Cerrar', onclick: close})),
  );
  document.body.append(dialog);
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Escape') {event.preventDefault(); event.stopPropagation(); close();}
  }, true);
  dialog.addEventListener('close', () => {sequence++; trigger.focus();});
  trigger.addEventListener('click', () => {dialog.showModal(); load();});
  month.addEventListener('change', load);
  search.addEventListener('input', render);

  function render() {
    tabs.forEach((tab, index) => {tab.setAttribute('aria-selected', String(active === index)); tab.tabIndex = active === index ? 0 : -1;});
    panel.setAttribute('aria-labelledby', `audit-tab-${active}`);
    table.replaceChildren();
    if (!data) return;
    const normalize = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const query = normalize(search.value);
    const labels = active ? ['Persona', 'Rol', 'Proyecto en GSE', 'Servicio asociado', 'Origen', 'Horas registradas / ajuste'] :
      ['Persona', 'Rol', 'Estimadas (h)', 'Registradas (h)', 'AER (h)', 'IXB (h)', 'RaaS (h)', 'SaaS (h)', 'T&M (h)', 'Otros (h)', 'Ajustes aprobados (h)'];
    const values = row => active ? [row.name, row.role, row.project, row.service, row.kind, row.hours] :
      [row.name, row.role, row.estimated, row.registered, ...['AER', 'IXB', 'RAAS', 'SAAS', 'TYM'].map(key => row.services[key] || 0),
        Object.entries(row.services).reduce((sum, [key, value]) => sum + (['AER', 'IXB', 'RAAS', 'SAAS', 'TYM'].includes(key) ? 0 : value), 0), row.adjustment];
    const numericFrom = active ? 5 : 2;
    const display = (value, index) => index >= numericFrom ? hours(value) : value;
    const all = (active ? data.projects : data.people).map(values);
    const rows = all.filter(row => row.some(value => normalize(value).includes(query)) &&
      [...filters[active]].every(([index, value]) => String(row[index] ?? '—') === value));
    const headings = labels.map((text, index) => {
      const options = [...new Set(all.map(row => String(row[index] ?? '—')))];
      options.sort((a, b) => index >= numericFrom && a !== '—' && b !== '—' ? Number(a) - Number(b) : a.localeCompare(b, 'es'));
      const select = el('select', {'aria-label': `Filtrar ${text}`, onchange: event => {
        if (event.target.value) filters[active].set(index, event.target.value);
        else filters[active].delete(index);
        render();
      }}, el('option', {value: '', text: 'Todos'}), ...options.map(value => el('option', {
        value, text: index >= numericFrom && value !== '—' ? hours(Number(value)) : value,
      })));
      select.value = filters[active].get(index) || '';
      return el('th', {scope: 'col'}, el('span', {text}), select);
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
        (data.published_revision ? `Existe cierre publicado (revisión ${data.published_revision}: ${data.published_source}). Este desglose consulta los registros actuales y puede diferir del cierre; no lo modifica.` : 'Mes sin cierre publicado por especialidad.');
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
