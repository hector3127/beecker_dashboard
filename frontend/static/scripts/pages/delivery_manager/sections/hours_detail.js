// @ts-check
// Detalle mensual: filtros locales, orden y paginación; conserva las cifras de origen.
import { el } from '#app/lib/dom.js';
import { icon } from './kpis.js';
import { findAccountLogo, loadAccountLogos } from '#app/lib/account-logos.js';

const KEYS = ['billable', 'operational', 'commercial'];
const LABELS = ['Facturables', 'Inversión operativa', 'Inversión comercial'];
const hours = value => `${Number(value || 0).toLocaleString('es-MX', {maximumFractionDigits: 1})} h`;
const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
function accountLogo(name) {
  const initials = name.trim().split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase();
  const host = el('span', {class: 'dm-account-logo', 'aria-hidden': 'true', text: initials || '—'});
  loadAccountLogos().then(items => {
    const logo = findAccountLogo(items, name);
    if (!logo) return;
    const image = el('img', {src: logo.url, alt: '', loading: 'lazy', decoding: 'async'});
    image.addEventListener('error', () => host.replaceChildren(initials || '—'), {once: true});
    host.replaceChildren(image);
  });
  return host;
}

export function detailDialog(months, csvRows, csvCell) {
  let selected = 0, page = 1, sortKey = 'total', direction = -1;
  const monthSelect = el('select', {id: 'hours-month', 'aria-label': 'Mes del detalle'}, ...months.map((month, index) => el('option', {value: index, text: month.label})));
  const search = el('input', {id: 'hours-search', type: 'search', placeholder: 'Buscar proyecto, cuenta o servicio…', 'aria-label': 'Buscar proyecto, cuenta o servicio'});
  const service = el('select', {id: 'hours-service', 'aria-label': 'Servicio del detalle'});
  const title = el('h2', {id: 'hours-modal-title', text: 'Detalle de horas'});
  const totals = el('div', {id: 'hours-totals', class: 'hours-totals', 'aria-label': 'Totales del mes completo'});
  const body = el('tbody', {id: 'hours-projects'});
  const count = el('span', {id: 'hours-count', role: 'status', 'aria-live': 'polite'});
  const pages = el('nav', {class: 'hours-pages', 'aria-label': 'Páginas de proyectos del mes'});
  const headers = [['name', 'ID / Proyecto'], ['client', 'Cuenta'], ['service', 'Servicio'], ['project_budget', 'Presupuesto proyecto (h)'], ['billable', 'Facturables'], ['operational', 'Inv. operativa'], ['commercial', 'Inv. comercial'], ['total', 'Total'], ['share', '% del mes']];
  const head = el('tr', {}, ...headers.map(([key, label]) => el('th', {scope: 'col', 'data-sort': key}, el('button', {type: 'button', text: label, onclick: () => {
    direction = sortKey === key ? -direction : (['name', 'client', 'service'].includes(key) ? 1 : -1);
    sortKey = key; page = 1; render();
  }}, el('span', {'aria-hidden': 'true', text: ' ↕'})))));
  const download = el('button', {type: 'button', class: 'hours-action', id: 'hours-download', text: '↓ Descargar CSV', title: 'Descargar todos los proyectos del mes seleccionado'});
  const dialog = el('dialog', {id: 'hours-modal', 'aria-labelledby': 'hours-modal-title'},
    el('div', {class: 'hours-detail-heading'}, icon('bars'), el('div', {}, title, el('p', {class: 'hs', text: 'Proyectos que componen las horas del mes seleccionado.'})), el('button', {type: 'button', id: 'hours-close', 'aria-label': 'Cerrar detalle', text: '×', onclick: () => dialog.close()})),
    el('div', {class: 'hours-controls'}, el('label', {class: 'hours-month-control'}, 'Mes', monthSelect), el('div', {class: 'hours-detail-filters'}, search, service, download)),
    totals,
    el('div', {class: 'table-scroll hours-detail-scroll', tabindex: '0', role: 'region', 'aria-label': 'Proyectos y horas del mes'}, el('table', {}, el('thead', {}, head), body)),
    el('div', {class: 'hours-detail-footer'}, count, pages),
    el('p', {class: 'hours-detail-note', text: 'Cada registro se cuenta una vez. El porcentaje usa el total del mes completo. CSV incluye todos los proyectos del mes.'}));

  function filtered() {
    return [...(months[selected]?.projects || [])].filter(project => normalize(`${project.id} ${project.name} ${project.client} ${project.service}`).includes(normalize(search.value)) && (!service.value || project.service === service.value)).sort((a, b) => {
      const key = sortKey === 'share' ? 'total' : sortKey;
      const av = a[key], bv = b[key];
      if (av == null) return bv == null ? 0 : 1;
      if (bv == null) return -1;
      return direction * (['name', 'client', 'service'].includes(key) ? String(av).localeCompare(String(bv), 'es', {numeric: true}) : Number(av) - Number(bv));
    });
  }
  function render() {
    const month = months[selected];
    const projects = filtered();
    const pageCount = Math.max(1, Math.ceil(projects.length / 10));
    page = Math.min(page, pageCount);
    head.querySelectorAll('th').forEach(th => th.setAttribute('aria-sort', th.dataset.sort === sortKey ? (direction === 1 ? 'ascending' : 'descending') : 'none'));
    const rows = projects.slice((page - 1) * 10, page * 10).map(project => el('tr', {},
      el('td', {class: 'hours-project-name'}, el('b', {text: project.name || project.id}), el('small', {text: project.id})),
      el('td', {}, el('span', {class: 'hours-account'}, accountLogo(project.client || ''), el('span', {text: project.client || 'Sin cuenta'}))),
      el('td', {}, el('span', {class: `dm-service service-${String(project.service || '').replace(/[^a-z]/gi, '').toLowerCase()}`, text: project.service || '—'})),
      el('td', {text: project.project_budget == null ? 'Sin presupuesto' : hours(project.project_budget)}),
      ...KEYS.map(key => el('td', {text: hours(project[key])})),
      el('td', {class: 'hours-emphasis', text: hours(project.total)}),
      el('td', {class: 'hours-emphasis hours-share', text: month.total > 0 ? `${(Number(project.total || 0) / month.total * 100).toLocaleString('es-MX', {maximumFractionDigits: 1})}%` : '—'})));
    body.replaceChildren(...(rows.length ? rows : [el('tr', {}, el('td', {colspan: 9, class: 'hours-empty', text: 'No hay proyectos que coincidan con los filtros.'}))]));
    count.textContent = projects.length ? `Mostrando ${(page - 1) * 10 + 1}–${Math.min(page * 10, projects.length)} de ${projects.length} proyectos` : '0 proyectos';
    const move = next => {page = next; render(); dialog.querySelector('.hours-detail-scroll').scrollTop = 0;};
    const numbers = Array.from({length: pageCount}, (_, index) => index + 1).filter(number => number === 1 || number === pageCount || Math.abs(number - page) <= 1);
    const buttons = [];
    numbers.forEach((number, index) => {
      if (index && number - numbers[index - 1] > 1) buttons.push(el('span', {text: '…'}));
      buttons.push(el('button', {type: 'button', 'aria-label': `Página ${number}`, 'aria-current': number === page ? 'page' : null, text: number, onclick: () => move(number)}));
    });
    pages.replaceChildren(el('button', {type: 'button', 'aria-label': 'Página anterior', text: '‹', disabled: page === 1, onclick: () => move(page - 1)}), ...buttons, el('button', {type: 'button', 'aria-label': 'Página siguiente', text: '›', disabled: page === pageCount, onclick: () => move(page + 1)}));
  }
  function fill(index) {
    selected = index; page = 1; monthSelect.value = String(index);
    const month = months[index];
    title.textContent = `Detalle de horas · ${month.label}`;
    const previousService = service.value;
    service.replaceChildren(el('option', {value: '', text: 'Todos los servicios'}), ...[...new Set(month.projects.map(p => p.service).filter(Boolean))].sort().map(value => el('option', {value, text: value})));
    service.value = [...service.options].some(option => option.value === previousService) ? previousService : '';
    totals.replaceChildren(...[['Total', month.total], ...KEYS.map((key, index) => [LABELS[index], month[key]])].map(([label, amount]) => el('span', {}, label, el('b', {text: hours(amount)}))));
    render();
  }
  monthSelect.addEventListener('change', () => fill(Number(monthSelect.value)));
  search.addEventListener('input', () => {page = 1; render();});
  service.addEventListener('change', () => {page = 1; render();});
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
  });
  download.addEventListener('click', () => {
    const month = months[selected];
    const text = csvRows(month).map(row => row.map(csvCell).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF' + text], {type: 'text/csv;charset=utf-8'}));
    el('a', {href: url, download: `horas-${month.label.replaceAll(' ', '-')}.csv`}).click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  return {dialog, open(index) {search.value = ''; service.value = ''; fill(index); if (!dialog.open) dialog.showModal();}};
}
