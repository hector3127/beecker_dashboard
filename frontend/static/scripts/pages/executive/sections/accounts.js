// @ts-check
// Comparacion de cuentas: busqueda, criterio y orden de cada grupo, guardados
// en la URL para que «regresar» desde una cuenta los encuentre igual.
import { withReturn } from '#app/data/navigation.js';
import { readParams, writeParams } from '#app/data/url-state.js';
import { el } from '#app/lib/dom.js';
import { formatCompact, formatNumber } from '#app/lib/format.js';
import { CRITERIA, rankAccounts } from '#app/lib/ranking.js';

const LABELS = { gross_profit: 'utilidad bruta', revenue: 'facturación', margin: 'margen bruto' };
const COLUMNS = /** @type {const} */ ([
  ['revenue', 'Facturación'],
  ['gross_profit', 'Utilidad bruta'],
  ['margin', 'Margen bruto (%)'],
]);
// Los nombres de grupo en la URL se conservan: guardan la busqueda de antes.
const GROUPS = /** @type {const} */ ([
  { kind: 'healthy', side: 'top', title: 'Cuentas sanas', hint: 'Mitad superior de las cuentas según el indicador seleccionado.', first: 'descending' },
  { kind: 'unhealthy', side: 'bottom', title: 'Cuentas no sanas', hint: 'Mitad inferior de las cuentas según el indicador seleccionado.', first: 'ascending' },
]);

/**
 * @param {HTMLElement} container
 * @param {import('#app/lib/ranking.js').RankedAccount[] | null} accounts null = el listado aun no esta preparado.
 * @param {{accountUrl: string, label: string, allAccountsUrl: string}} options accountUrl lleva el marcador ACCOUNT_SLUG.
 */
export function renderAccounts(container, accounts, { accountUrl, label, allAccountsUrl }) {
  const search = /** @type {HTMLInputElement} */ (el('input', { id: 'ranking-search', type: 'search', placeholder: 'Nombre de la cuenta…', autocomplete: 'off' }));
  const select = /** @type {HTMLSelectElement} */ (
    el('select', { id: 'ranking-sort' }, el('option', { value: 'gross_profit', text: 'Utilidad bruta ($)' }), el('option', { value: 'revenue', text: 'Facturación ($)' }), el('option', { value: 'margin', text: 'Margen bruto (%)' }))
  );
  const coverage = el('p', { id: 'ranking-coverage', role: 'status', 'aria-live': 'polite' });
  const params = readParams();
  const defaults = () => ({ healthy: 'descending', unhealthy: 'ascending' });
  let directions = /** @type {Record<string, string>} */ (defaults());
  search.value = params.get('ranking_buscar') || '';
  const saved = params.get('ranking_criterio');
  if (CRITERIA.includes(/** @type {any} */ (saved))) select.value = /** @type {string} */ (saved);
  for (const { kind } of GROUPS) {
    const direction = params.get(`ranking_${kind}`);
    if (direction === 'ascending' || direction === 'descending') directions[kind] = direction;
  }

  const cards = GROUPS.map((group) => {
    const count = el('span', { class: 'ranking-count', id: `${group.kind}-account-count`, 'aria-live': 'polite', text: 'Consultando' });
    const body = el('tbody', { id: `${group.kind}-financial-accounts` });
    const heads = COLUMNS.map(([key, text]) => {
      const indicator = el('span', { 'aria-hidden': 'true', text: '↕' });
      const th = el('th', { scope: 'col' }, el('button', { type: 'button', text: `${text} `, onclick: () => sortBy(group.kind, key) }, indicator));
      return { key, th, indicator };
    });
    const node = el(
      'section',
      { class: `card ranking-card ${group.kind}` },
      el('div', { class: 'ranking-heading' }, el('div', {}, el('h3', { text: `${group.title} · ${label}` }), el('p', { class: 'note', text: `${group.hint} Hasta 5 resultados.` })), count),
      el('div', { class: 'ranking-scroll', tabindex: 0, role: 'region', 'aria-label': group.title }, el('table', {}, el('caption', { class: 'sr-only', text: `${group.title}. Ordena mediante los encabezados.` }), el('thead', {}, el('tr', {}, el('th', { scope: 'col', text: '#' }), el('th', { scope: 'col', text: 'Cuenta' }), ...heads.map((h) => h.th))), body)),
    );
    return { group, count, body, heads, node };
  });

  /** @param {string} kind @param {string} key */
  function sortBy(kind, key) {
    if (select.value === key) directions[kind] = directions[kind] === 'ascending' ? 'descending' : 'ascending';
    else {
      select.value = key;
      directions = defaults();
    }
    draw();
  }

  /** @param {number | null | undefined} value @param {string} suffix */
  const num = (value, suffix) => (value == null || !Number.isFinite(Number(value)) ? 'No aplica' : `${formatNumber(Number(value), 2)}%${suffix}`);

  function draw() {
    const list = /** @type {import('#app/lib/ranking.js').RankedAccount[]} */ (accounts);
    const result = rankAccounts(list, select.value, search.value, { top: /** @type {any} */ (directions.healthy), bottom: /** @type {any} */ (directions.unhealthy) });
    for (const { group, count, body, heads } of cards) {
      const view = result[group.side];
      count.textContent = `${view.rows.length} de ${view.count} cuentas`;
      body.replaceChildren(
        ...(view.rows.length
          ? view.rows.map((account, index) => {
              const star = account.partial ? '*' : '';
              const slug = /** @type {any} */ (account).slug;
              const base = accountUrl.replace('ACCOUNT_SLUG', slug) + `?nombre=${encodeURIComponent(account.name)}`;
              // El regreso recuerda la busqueda y el orden de este momento, no los del dibujo.
              const link = el('a', { class: 'ranking-account', href: base, text: account.name });
              link.addEventListener('click', () => (/** @type {HTMLAnchorElement} */ (link).href = withReturn(base)));
              return el(
                'tr',
                {},
                el('td', { text: String(index + 1) }),
                el('td', {}, link, el('small', { text: `${account.projects ?? 0} proyectos${star ? ' · Parcial*' : ''}` })),
                el('td', { class: 'n', text: formatCompact(account.revenue) }),
                el('td', { class: 'n' }, el('strong', { text: formatCompact(account.gross_profit) + star })),
                el('td', { class: 'n' }, el('b', { text: num(account.margin, star) })),
              );
            })
          : [el('tr', {}, el('td', { colspan: 5, text: 'No hay cuentas con datos para este grupo y búsqueda.' }))]),
      );
      for (const head of heads) {
        const active = head.key === select.value;
        const th = /** @type {HTMLElement} */ (head.th);
        if (active) th.setAttribute('aria-sort', directions[group.kind]);
        else th.removeAttribute('aria-sort');
        head.indicator.textContent = active ? (directions[group.kind] === 'ascending' ? '↑' : '↓') : '↕';
      }
    }
    const what = LABELS[/** @type {keyof typeof LABELS} */ (result.criterion)];
    coverage.textContent =
      `${result.eligible} ${result.eligible === 1 ? 'cuenta comparada' : 'cuentas comparadas'} por ${what}. ` +
      (result.missing ? `${result.missing} sin dato para este criterio. ` : '') +
      (result.partial ? `${result.partial} ${result.partial === 1 ? 'cuenta con costos parciales (*).' : 'cuentas con costos parciales (*).'}` : 'Sin ponderación 70/30.');
    writeParams({
      ranking_buscar: search.value,
      ranking_criterio: select.value === 'gross_profit' ? '' : select.value,
      ranking_healthy: directions.healthy === 'descending' ? '' : directions.healthy,
      ranking_unhealthy: directions.unhealthy === 'ascending' ? '' : directions.unhealthy,
    });
  }

  container.replaceChildren(
    el(
      'section',
      { class: 'card ranking-section', 'aria-labelledby': 'ranking-section-title' },
      el('div', { class: 'ranking-section-heading' }, el('h2', { id: 'ranking-section-title', text: 'Rentabilidad por cuenta' }), el('a', { href: allAccountsUrl, text: 'Ver todas las cuentas →' })),
      el('div', { class: 'ranking-controls', id: 'account-ranking-controls' }, el('div', {}, el('label', { for: 'ranking-search', text: 'Buscar cuenta' }), search), el('div', {}, el('label', { for: 'ranking-sort', text: 'Comparar cuentas por' }), select), coverage),
      el('div', { class: 'ranking-groups' }, ...cards.map((c) => c.node)),
      el('p', { class: 'note', text: 'Los grupos indican posiciones relativas según el criterio elegido, no una evaluación integral de la cuenta. Haz clic en una columna para cambiar el orden. * Costos y márgenes parciales sujetos a cambios.' }),
    ),
  );

  if (accounts === null) {
    search.disabled = select.disabled = true;
    for (const { count, body, heads } of cards) {
      count.textContent = 'Pendiente';
      body.replaceChildren(el('tr', {}, el('td', { colspan: 5, text: 'Listado completo de cuentas pendiente de preparar.' })));
      heads.forEach((h) => h.th.querySelector('button')?.setAttribute('disabled', ''));
    }
    coverage.textContent = 'El listado completo de cuentas está pendiente de preparar. Actualiza los datos para habilitar la comparación.';
    return;
  }
  search.addEventListener('input', draw);
  select.addEventListener('change', () => ((directions = defaults()), draw()));
  draw();
}
