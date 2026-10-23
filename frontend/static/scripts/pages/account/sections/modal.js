// @ts-check
// Ventana de detalle de la cuenta y los helpers para llenarla.
import { svg } from '#app/lib/dom.js';
import { hours } from './kpis.js';

/**
 * Crea un nodo, le pone texto y clase y lo agrega a su contenedor.
 * @param {string} tag
 * @param {string | number | null} text
 * @param {Node | null} [parent]
 * @param {string} [className]
 * @returns {HTMLElement}
 */
export function element(tag, text, parent, className) {
  const node = document.createElement(tag);
  if (text !== null) node.textContent = String(text);
  if (className) node.className = className;
  if (parent) parent.append(node);
  return node;
}

/** @param {Node} parent @param {string} tag @param {Record<string, string | number>} attrs @param {string} [text] */
export function shape(parent, tag, attrs, text) {
  const node = svg(tag, attrs, ...(text === undefined ? [] : [text]));
  parent.appendChild(node);
  return node;
}

export { hours };

/** El dialogo de detalle, con su titulo y su boton de cierre. */
export function createModal() {
  const modal = /** @type {HTMLDialogElement} */ (document.createElement('dialog'));
  modal.id = 'account-detail-modal';
  const header = element('header', null, modal);
  element('h2', null, header).id = 'account-detail-title';
  const close = element('button', '×', header);
  close.id = 'account-detail-close';
  close.setAttribute('aria-label', 'Cerrar');
  close.addEventListener('click', () => modal.close());
  element('div', null, modal).id = 'account-detail-content';

  /** Limpia la ventana, pone el titulo y la abre. @param {string} title */
  function start(title) {
    modal.classList.remove('budget-layout');
    /** @type {HTMLElement} */ (document.getElementById('account-detail-title')).textContent = title;
    const root = /** @type {HTMLElement} */ (document.getElementById('account-detail-content'));
    root.replaceChildren();
    if (!modal.open) modal.showModal();
    return root;
  }
  return { modal, start };
}

/**
 * Tabla con busqueda, filtro por una columna, orden y paginas de ocho.
 * @param {ReturnType<typeof createModal>} detail
 * @param {string} title
 * @param {string[]} headers
 * @param {any[][]} items
 * @param {number} stageIndex Columna por la que filtra el selector.
 */
export function filteredTable(detail, title, headers, items, stageIndex) {
  const root = detail.start(title);
  const controls = element('div', null, root, 'detail-controls');
  const search = /** @type {HTMLInputElement} */ (element('input', null, controls));
  const stage = /** @type {HTMLSelectElement} */ (element('select', null, controls));
  search.placeholder = 'Buscar cuenta o proyecto…';
  /** @type {HTMLOptionElement} */ (element('option', 'Todos los estados', stage)).value = '';
  [...new Set(items.map((row) => row[stageIndex]))].filter(Boolean).forEach((value) => element('option', value, stage));
  const table = element('table', null, root);
  const head = element('tr', null, table);
  const body = element('tbody', null, table);
  const pager = element('div', null, root, 'detail-pager');
  let page = 1;
  let sort = 0;
  let ascending = true;
  headers.forEach((label, index) => {
    const th = element('th', `${label} ↕`, head);
    th.style.cursor = 'pointer';
    th.onclick = () => {
      ascending = sort === index ? !ascending : true;
      sort = index;
      draw();
    };
  });

  function draw() {
    const wanted = search.value.toLocaleLowerCase('es');
    const filtered = items
      .filter((row) => row.join(' ').toLocaleLowerCase('es').includes(wanted) && (!stage.value || row[stageIndex] === stage.value))
      .sort((a, b) => String(a[sort]).localeCompare(String(b[sort]), 'es', { numeric: true }) * (ascending ? 1 : -1));
    const pages = Math.max(1, Math.ceil(filtered.length / 8));
    page = Math.max(1, Math.min(page, pages));
    body.replaceChildren();
    for (const row of filtered.slice((page - 1) * 8, page * 8)) {
      const tr = element('tr', null, body);
      for (const value of row) element('td', value, tr);
    }
    pager.replaceChildren();
    element('span', `${filtered.length} registros · página ${page} de ${pages}`, pager);
    const buttons = element('div', null, pager);
    const prev = /** @type {HTMLButtonElement} */ (element('button', '←', buttons));
    const next = /** @type {HTMLButtonElement} */ (element('button', '→', buttons));
    prev.disabled = page === 1;
    next.disabled = page === pages;
    prev.onclick = () => {
      page -= 1;
      draw();
    };
    next.onclick = () => {
      page += 1;
      draw();
    };
  }
  search.oninput = stage.onchange = () => {
    page = 1;
    draw();
  };
  draw();
}
