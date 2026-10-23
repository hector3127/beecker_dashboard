// @ts-check
// Decisiones y seguimiento: acuerdos y pendientes de direccion y consejo.
// Los datos y los cambios pasan por /api/v1/agreements/; este modulo solo
// pinta la tabla y el formulario.
import { apiGet, apiSend } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { plain } from '#app/lib/format.js';

const STATUS = { open: 'Abierto', progress: 'En curso', done: 'Completado' };
const COLUMNS = ['Cuenta / acuerdo', 'Sesión', 'Tipo', 'Seguimiento', 'Acción', 'Compromiso', 'Estado', 'Acciones'];
const HEADINGS = ['Cuenta / acuerdo', 'Sesión', 'Prioridad / tipo', 'Situación / seguimiento', 'Acción / acuerdo', 'Compromiso', 'Estado', 'Acciones'];
const FIELDS = ['id', 'account', 'meeting_source', 'meeting_date', 'title', 'kind', 'owner', 'due_date', 'status', 'notes'];

/** "2026-10-21" -> "21/10/2026". @param {string} iso */
const dmy = (iso) => iso.split('-').reverse().join('/');

/**
 * @param {string} name @param {string} label
 * @param {[string, string][]} options
 */
function select(name, label, options) {
  return el('label', {}, label, el('select', { name }, ...options.map(([value, text]) => el('option', { value, text }))));
}

/** @param {string} label @param {Record<string, any>} attrs */
const input = (label, attrs) => el('label', {}, label, el('input', attrs));

/**
 * @param {{account?: string, accounts?: string[]}} options account acota la
 *   vista a una cuenta; accounts son las que se pueden elegir sin acotar.
 * @returns {HTMLElement}
 */
export function createAgreements({ account = '', accounts = [] } = {}) {
  const accountOptions = account
    ? [[account, account]]
    : [['', 'Selecciona una cuenta'], ...accounts.map((name) => [name, name])];
  const form = /** @type {HTMLFormElement} */ (
    el(
      'form',
      { id: 'agreement-form', hidden: true },
      el('input', { type: 'hidden', name: 'id' }),
      select('account', 'Cuenta', /** @type {[string, string][]} */ (accountOptions)),
      select('meeting_source', 'Origen', [['direction', 'Dirección'], ['board', 'Consejo']]),
      input('Fecha de sesión', { name: 'meeting_date', type: 'date', required: true }),
      input('Título', { name: 'title', maxlength: 200, required: true }),
      select('kind', 'Tipo', [['pending', 'Pendiente'], ['agreement', 'Acuerdo']]),
      el('input', { type: 'hidden', name: 'owner' }),
      input('Fecha compromiso', { type: 'date', name: 'due_date' }),
      select('status', 'Estado', [['open', 'Abierto'], ['progress', 'En curso'], ['done', 'Completado']]),
      el('label', { class: 'agreement-notes' }, 'Detalle / seguimiento', el('textarea', { name: 'notes', maxlength: 2000, rows: 2 })),
      el(
        'div',
        { class: 'agreement-form-actions' },
        el('button', { type: 'button', id: 'agreement-cancel', text: 'Cancelar' }),
        el('button', { type: 'submit', id: 'agreement-save', text: 'Guardar' }),
      ),
    )
  );
  const search = /** @type {HTMLInputElement} */ (
    el('input', {
      type: 'search',
      id: 'agreement-search',
      placeholder: account ? 'Buscar pendiente o acuerdo…' : 'Buscar cuenta o acuerdo…',
      'aria-label': 'Buscar decisiones, acuerdos o pendientes',
    })
  );
  const filter = /** @type {HTMLSelectElement} */ (
    el(
      'select',
      { id: 'agreement-filter', 'aria-label': 'Filtrar por estado' },
      el('option', { value: '', text: account ? 'Todos los pendientes' : 'Todos los estados' }),
      el('option', { value: 'open', text: 'Abiertos / por atender' }),
      el('option', { value: 'progress', text: 'En curso' }),
      ...(account ? [] : [el('option', { value: 'done', text: 'Completados' })]),
    )
  );
  const feedback = el('span', { id: 'agreement-feedback', role: 'status', 'aria-live': 'polite' });
  const body = el('tbody', { id: 'agreement-rows' }, el('tr', {}, el('td', { colspan: 8, text: 'Consultando acuerdos de dirección y consejo…' })));
  const newButton = /** @type {HTMLButtonElement} */ (el('button', { type: 'button', id: 'agreement-new', text: '+ Agregar acuerdo o pendiente' }));
  const section = el(
    'section',
    { class: 'c p executive-followup executive-agreements', 'aria-labelledby': 'followup-title', id: 'executive-agreements' },
    el(
      'div',
      { class: 'agreements-heading' },
      el(
        'div',
        {},
        el('h3', { id: 'followup-title', text: 'Decisiones y seguimiento' }),
        el('p', {
          class: 'note',
          text: account ? `Pendientes y acuerdos abiertos o en curso de ${account}.` : 'Acuerdos de sesiones de dirección y consejo, organizados por cuenta.',
        }),
      ),
      newButton,
    ),
    form,
    el('div', { class: 'agreement-toolbar' }, search, filter, feedback),
    el(
      'div',
      { class: 'executive-table-scroll' },
      el('table', {}, el('thead', {}, el('tr', {}, ...HEADINGS.map((text) => el('th', { text })))), body),
    ),
  );

  /** @type {any[]} */
  let items = [];
  let canEdit = true;
  const field = (/** @type {string} */ name) => /** @type {HTMLInputElement} */ (form.elements.namedItem(name));

  /** @param {any} [item] */
  function edit(item = {}) {
    form.reset();
    if (account) field('account').value = account;
    const accountSelect = /** @type {HTMLSelectElement} */ (form.elements.namedItem('account'));
    if (item.account && ![...accountSelect.options].some((option) => option.value === item.account)) {
      accountSelect.add(new Option(item.account, item.account));
    }
    for (const key of FIELDS) if (item[key] !== null && item[key] !== undefined && field(key)) field(key).value = item[key];
    form.hidden = false;
    field('account').focus();
    feedback.textContent = '';
  }

  /** @param {{items: any[], can_edit?: boolean}} data */
  function sync(data) {
    items = data.items;
    canEdit = data.can_edit !== false;
    newButton.hidden = !canEdit;
  }

  /** Mensaje de un error de la API, con los campos que fallaron. @param {any} error */
  const message = (error) => {
    const fields = error && error.fields ? Object.values(error.fields).flat().join(' ') : '';
    return fields || (error instanceof Error && error.message) || 'Revisa los campos del acuerdo.';
  };

  /** @param {any} item @param {string} status */
  async function setStatus(item, status) {
    if (status === item.status) return;
    feedback.textContent = 'Guardando estado…';
    try {
      const { data } = await apiSend('PATCH', `agreements/${item.id}/`, { status });
      items = items.map((row) => (row.id === data.id ? data : row));
      feedback.textContent = status === 'done' ? 'Completado.' : 'Estado actualizado.';
    } catch (error) {
      feedback.textContent = message(error);
    }
    draw();
  }

  /** @param {any} item */
  function row(item) {
    const cell = (/** @type {Node | string} */ content, /** @type {string} */ className = '') => {
      const td = el('td', { class: className || null, 'data-label': COLUMNS[tr.children.length] }, content);
      tr.append(td);
      return td;
    };
    const tr = el('tr');
    const when = item.meeting_date ? `${item.meeting_source === 'board' ? 'Consejo' : 'Dirección'} · ${dmy(item.meeting_date)}` : 'Sesión pendiente de identificar';
    cell(item.title);
    cell(when);
    cell(item.kind === 'agreement' ? 'Acuerdo' : 'Pendiente');
    cell(item.notes || '—');
    cell(item.kind === 'agreement' ? 'Cumplir acuerdo' : 'Dar seguimiento');
    cell(item.due_date ? dmy(item.due_date) : 'Sin fecha');
    const state = /** @type {HTMLSelectElement} */ (
      el(
        'select',
        { class: `agreement-status agreement-status-select ${item.status}`, 'aria-label': `Cambiar estado de ${item.title}` },
        ...Object.entries(STATUS).map(([value, text]) => el('option', { value, text })),
      )
    );
    state.value = item.status;
    state.disabled = !canEdit || !item.actions?.change_status;
    state.addEventListener('change', () => setStatus(item, state.value));
    cell(state);
    const actions = cell('', 'agreement-row-actions');
    if (canEdit && item.actions?.edit) actions.append(el('button', { type: 'button', text: 'Editar', onclick: () => edit(item) }));
    if (canEdit && item.status !== 'done' && item.actions?.change_status) {
      actions.append(
        el('button', { type: 'button', class: 'agreement-close', text: 'Cerrar', 'aria-label': `Completar ${item.title}`, onclick: () => setStatus(item, 'done') }),
      );
    }
    return tr;
  }

  function draw() {
    const wanted = plain(search.value);
    const list = items
      .filter((x) => (!account || x.status !== 'done') && (!filter.value || x.status === filter.value) && plain([x.account, x.title, x.notes].join(' ')).includes(wanted))
      .sort((a, b) => (a.account || '~').localeCompare(b.account || '~') || String(b.meeting_date || '').localeCompare(String(a.meeting_date || '')));
    const rows = [];
    let previous = null;
    for (const item of list) {
      const name = item.account || 'Sin cuenta · pendiente de clasificar';
      if (name !== previous) {
        rows.push(el('tr', { class: 'agreement-account-group' }, el('td', { colspan: 8, 'data-label': COLUMNS[0], text: name })));
        previous = name;
      }
      rows.push(row(item));
    }
    if (!list.length) rows.push(el('tr', {}, el('td', { colspan: 8, text: 'Sin acuerdos de dirección o consejo registrados para esta búsqueda.' })));
    body.replaceChildren(...rows);
  }

  newButton.addEventListener('click', () => edit());
  section.querySelector('#agreement-cancel')?.addEventListener('click', () => {
    form.hidden = true;
  });
  search.addEventListener('input', draw);
  filter.addEventListener('change', draw);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const save = /** @type {HTMLButtonElement} */ (form.querySelector('#agreement-save'));
    save.disabled = true;
    /** @type {Record<string, string>} */
    const values = {};
    for (const key of FIELDS) if (key !== 'id' && field(key)) values[key] = field(key).value;
    const id = field('id').value;
    try {
      const { data } = await (id ? apiSend('PATCH', `agreements/${id}/`, values) : apiSend('POST', 'agreements/', values));
      items = id ? items.map((row) => (row.id === data.id ? data : row)) : [...items, data];
      form.hidden = true;
      feedback.textContent = 'Guardado.';
      draw();
    } catch (error) {
      feedback.textContent = message(error);
    } finally {
      save.disabled = false;
    }
  });

  apiGet('agreements/', { account: account || null, pending_only: account ? 1 : null })
    .then(({ data }) => {
      sync(data);
      draw();
    })
    .catch(() => {
      feedback.textContent = 'No se pudieron consultar los acuerdos. Intenta de nuevo.';
    });
  return section;
}
