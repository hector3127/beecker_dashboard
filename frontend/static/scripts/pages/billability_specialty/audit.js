import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';

const format = new Intl.NumberFormat('es-MX', {maximumFractionDigits: 2});
const hours = value => value == null ? '—' : format.format(value);

export function bindAudit() {
  const trigger = document.getElementById('specialty-audit-open');
  if (!trigger) return;
  const months = JSON.parse(document.getElementById('specialty-audit-months')?.textContent || '[]');
  let data = null;
  let active = 0;
  let sequence = 0;
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
    el('div', {class: 'audit-controls'}, el('label', {}, 'Mes ', month), search, retry),
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
    const query = search.value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const rows = (active ? data.projects : data.people).filter(row =>
      Object.values(row).join(' ').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().includes(query));
    const labels = active ? ['Persona', 'Rol', 'Proyecto en GSE', 'Servicio asociado', 'Origen', 'Horas registradas / ajuste'] :
      ['Persona', 'Rol', 'Estimadas (h)', 'Registradas (h)', 'AER (h)', 'IXB (h)', 'RaaS (h)', 'SaaS (h)', 'T&M (h)', 'Otros (h)', 'Ajustes aprobados (h)'];
    const values = row => active ? [row.name, row.role, row.project, row.service, row.kind, hours(row.hours)] :
      [row.name, row.role, hours(row.estimated), hours(row.registered), ...['AER', 'IXB', 'RAAS', 'SAAS', 'TYM'].map(key => hours(row.services[key] || 0)),
        hours(Object.entries(row.services).reduce((sum, [key, value]) => sum + (['AER', 'IXB', 'RAAS', 'SAAS', 'TYM'].includes(key) ? 0 : value), 0)), hours(row.adjustment)];
    const body = el('tbody', {}, ...rows.map(row => el('tr', {}, ...values(row).map(value => el('td', {text: value})))));
    if (!rows.length) body.append(el('tr', {}, el('td', {colspan: labels.length, text: 'Sin coincidencias para este mes, áreas y búsqueda.'})));
    table.append(el('table', {}, el('thead', {}, el('tr', {}, ...labels.map(text => el('th', {scope: 'col', text})))), body));
    status.textContent = `${rows.length} ${active ? 'registros agrupados por proyecto y servicio' : 'personas'} · ${month.value}`;
  }

  async function load() {
    const current = ++sequence;
    data = null; render();
    status.textContent = 'Cargando desglose…';
    panel.setAttribute('aria-busy', 'true');
    source.textContent = '';
    const params = new URLSearchParams(location.search);
    try {
      const response = await apiGet('screens/facturabilidad/desglose/', {params: {
        mes: month.value, roles: params.get('roles'), rol: params.getAll('rol'),
      }});
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
