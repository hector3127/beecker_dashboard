// @ts-check
// Rentabilidad por cuenta: dos grupos (mitad superior e inferior) segun el
// criterio elegido, con busqueda y orden por columna guardados en la URL.
import { findAccountLogo, loadAccountLogos } from '#app/lib/account-logos.js';
import { CRITERIA, numeric, rankAccounts } from '#app/lib/ranking.js';
import { el } from '#app/lib/dom.js';
import { formatCompact, plain } from '#app/lib/format.js';

const KINDS = /** @type {const} */ (['healthy', 'unhealthy']);
const LABELS = { gross_profit: 'utilidad bruta', revenue: 'facturación', margin: 'margen bruto' };
let mounted=0;
function avatar(name,url){
  const words=String(name).trim().split(/\s+/);
  const text=words.length===1?words[0].slice(0,3).toUpperCase():words.slice(0,2).map(word=>word[0]).join('').toUpperCase();
  const node=el('span',{class:'ranking-logo','aria-hidden':'true'});
  const fallback=()=>{node.replaceChildren();node.dataset.initials=text;};
  fallback();
  if(url){const img=el('img',{src:url,alt:'',loading:'lazy',decoding:'async'});img.addEventListener('error',fallback,{once:true});node.replaceChildren(img);delete node.dataset.initials;}
  return node;
}
const defaults = () => ({ healthy: 'descending', unhealthy: 'ascending' });

/** @param {string} id */
const byId = (id) => /** @type {HTMLElement} */ (document.getElementById(id));

/** @param {any} account @param {number} index @param {(account: any) => string} href */
function rankRow(account, index, href, logos) {
  const partial = account.pending || account.partial ? '*' : '';
  const margin = numeric(account.margin) ? `${Number(account.margin).toLocaleString('es-MX', { maximumFractionDigits: 2 })}%${partial}` : 'No aplica';
  return el(
    'tr',
    {},
    el('td', { text: index + 1 }),
    el('td', {}, el('a', { class: 'ranking-account', href: href(account) },avatar(account.name,findAccountLogo(logos,account.name)?.url),el('span',{text:account.name})), el('small', { text: `${account.projects ?? 0} proyectos${partial ? ' · Parcial*' : ''}` })),
    el('td', { class: 'ranking-revenue', text: formatCompact(account.revenue) }),
    el('td', { class: `ranking-margin ${numeric(account.gross_profit) && Number(account.gross_profit) < 0 ? 'ranking-negative' : 'ranking-positive'}` }, el('strong', { text: formatCompact(account.gross_profit) + partial })),
    el('td', { class: `ranking-margin ${numeric(account.margin) && Number(account.margin) < 0 ? 'ranking-negative' : 'ranking-positive'}` }, el('b', { text: margin })),
  );
}

/**
 * @param {any[] | null} accounts Cuentas del corte; null si el listado no esta preparado.
 * @param {(account: any) => string} href Destino de cada cuenta.
 */
export function mountRankings(accounts, href) {
  const version=++mounted;
  let logos=[];
  const search = /** @type {HTMLInputElement} */ (byId('ranking-search'));
  const select = /** @type {HTMLSelectElement} */ (byId('ranking-sort'));
  const status = byId('ranking-coverage');
  if (!Array.isArray(accounts)) {
    search.disabled = true;
    select.disabled = true;
    document.querySelectorAll('[data-sort-key]').forEach((button) => {
      /** @type {HTMLButtonElement} */ (button).disabled = true;
    });
    for (const kind of KINDS) {
      byId(`${kind}-account-count`).textContent = 'Pendiente';
      byId(`${kind}-financial-accounts`).replaceChildren(el('tr', {}, el('td', { colspan: 5, text: 'Listado completo de cuentas pendiente de preparar.' })));
    }
    status.textContent = 'El listado completo de cuentas está pendiente de preparar. Actualiza los datos para habilitar la comparación.';
    return;
  }
  /** @type {{healthy: string, unhealthy: string}} */
  let directions = defaults();
  const saved = new URLSearchParams(location.search);
  search.value = saved.get('ranking_buscar') || '';
  const criterion = saved.get('ranking_criterio');
  if (criterion && CRITERIA.includes(criterion)) select.value = criterion;
  for (const kind of KINDS) {
    const direction = saved.get(`ranking_${kind}`);
    if (direction === 'ascending' || direction === 'descending') directions[kind] = direction;
  }

  function draw() {
    const result = rankAccounts(accounts || [], select.value, search.value, /** @type {any} */ (directions));
    for (const kind of KINDS) {
      const group = result[kind];
      const body = byId(`${kind}-financial-accounts`);
      byId(`${kind}-account-count`).textContent = `${group.rows.length} de ${group.count} cuentas`;
      body.replaceChildren(...(group.rows.length ? group.rows.map((/** @type {any} */ a, /** @type {number} */ i) => rankRow(a, i, href, logos)) : [el('tr', {}, el('td', { colspan: 5, text: 'No hay cuentas con datos para este grupo y búsqueda.' }))]));
      const table = /** @type {HTMLElement} */ (body.closest('table'));
      table.querySelectorAll('[data-ranking-column]').forEach((header) => {
        const active = /** @type {HTMLElement} */ (header).dataset.rankingColumn === select.value;
        if (active) header.setAttribute('aria-sort', directions[kind]);
        else header.removeAttribute('aria-sort');
        /** @type {HTMLElement} */ (header.querySelector('[data-sort-indicator]')).textContent = active ? (directions[kind] === 'ascending' ? '↑' : '↓') : '↕';
      });
    }
    const wanted = plain(search.value);
    const key = /** @type {'gross_profit' | 'revenue' | 'margin'} */ (select.value);
    const partial = (accounts || []).filter((a) => plain(String(a.name)).includes(wanted) && numeric(a[key]) && (a.pending || a.partial)).length;
    status.textContent =
      `${result.eligible}${result.eligible === 1 ? ' cuenta comparada por ' : ' cuentas comparadas por '}${LABELS[key]}. ` +
      (result.missing ? `${result.missing} sin dato para este criterio. ` : '') +
      (partial ? `${partial}${partial === 1 ? ' cuenta con costos parciales (*).' : ' cuentas con costos parciales (*).'}` : 'Sin ponderación 70/30.');
    const current = new URL(location.href);
    /** @type {[string, string][]} */
    const params = [
      ['ranking_buscar', search.value],
      ['ranking_criterio', select.value === 'gross_profit' ? '' : select.value],
      ...KINDS.map(/** @returns {[string, string]} */ (kind) => [`ranking_${kind}`, directions[kind] === defaults()[kind] ? '' : directions[kind]]),
    ];
    for (const [name, value] of params) {
      if (value) current.searchParams.set(name, value);
      else current.searchParams.delete(name);
    }
    history.replaceState(history.state, '', current.pathname + current.search + current.hash);
  }

  search.addEventListener('input', draw);
  select.addEventListener('change', () => {
    directions = defaults();
    draw();
  });
  document.querySelectorAll('[data-sort-key]').forEach((node) =>
    node.addEventListener('click', () => {
      const button = /** @type {HTMLElement} */ (node);
      const kind = /** @type {'healthy' | 'unhealthy'} */ (button.dataset.rankingGroup);
      const key = /** @type {string} */ (button.dataset.sortKey);
      if (select.value === key) directions[kind] = directions[kind] === 'ascending' ? 'descending' : 'ascending';
      else {
        select.value = key;
        directions = defaults();
      }
      draw();
    }),
  );
  draw();
  loadAccountLogos().then(items=>{if(version!==mounted)return;logos=items;draw();});
}
