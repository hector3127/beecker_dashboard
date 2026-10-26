// @ts-check
// Delivery Manager: la base llega primero; inversion y horas despues, en paralelo.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { loadingHours, renderHours } from './sections/hours.js';
import { loadingCards, renderCards, renderHead, subtitle } from './sections/kpis.js';
import { downloadProjects, loadingTable, renderTable } from './sections/projects.js';

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
const app = byId('dm-app');
const { slug = '', projectUrl = '', accountUrl = '', operativaUrl = '/' } = app.dataset;
const head = byId('dm-head');
const kpis = byId('dm-kpis');
const table = byId('dm-table');
const monthly = byId('dm-monthly');
const errors = byId('dm-error');
const noteError = byId('dm-note-error');
const name = head.querySelector('h1')?.textContent || '';
const urls = { project: projectUrl, account: accountUrl };

/** Aviso en una region, con enlace para reintentar. @param {HTMLElement} region @param {string} text */
function fail(region, text) {
  const box = el('div', { class: 'err', role: 'alert' }, `${text} `, el('a', { href: location.pathname + location.search, text: 'Reintentar' }));
  region.prepend(box);
}

/** @param {'base' | 'inv' | 'horas'} stage */
const load = (stage) => apiGet(`screens/delivery-managers/${encodeURIComponent(slug)}/`, { bloque: stage }).then((body) => body.data);

/** @param {any} data */
function draw(data) {
  head.replaceChildren(...renderHead(data.name, data.initials, subtitle(data.summary)),el('div',{class:'dm-head-actions'},el('span',{id:'dm-period',text:app.dataset.periodLabel||'Últimos 6 meses disponibles'}),el('button',{type:'button',id:'dm-project-export',text:'↓ Exportar CSV',onclick:()=>downloadProjects(data)})));
  kpis.removeAttribute('aria-busy');
  kpis.replaceChildren(...renderCards(data));
  table.replaceChildren(...renderTable(data, urls));
  noteError.textContent = data.investment.error;
}

/** @param {unknown} error */
function unavailable(error) {
  // Como antes: si las fuentes no responden, se vuelve a Operativa.
  if (error && typeof error === 'object' && 'code' in error && error.code === 'upstream') {
    location.replace(operativaUrl);
    return;
  }
  const message = error instanceof Error ? error.message : 'No se pudo cargar el detalle.';
  errors.replaceChildren(el('div', { class: 'err', role: 'alert' }, message));
}

async function start() {
  kpis.replaceChildren(...loadingCards());
  table.replaceChildren(...loadingTable(name));
  monthly.replaceWith(loadingHours());
  let base;
  try {
    base = await load('base');
  } catch (error) {
    unavailable(error);
    return;
  }
  draw(base);
  await Promise.all([
    load('inv')
      .then(draw)
      .catch(() => fail(table, 'No se pudo cargar la inversión y los riesgos.')),
    load('horas')
      .then((data) => {const months=data.hours.months;app.dataset.periodLabel=months.length?`${months[0].label} – ${months.at(-1).label}`:'Periodo sin registros';const label=byId('dm-period');if(label)label.textContent=app.dataset.periodLabel;byId('dm-monthly').replaceWith(renderHours(data.hours,data.name));})
      .catch(() => fail(byId('dm-monthly'), 'No se pudo cargar el consumo de horas.')),
  ]);
}

start();
