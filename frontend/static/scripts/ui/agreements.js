// @ts-check
// Decisiones y seguimiento de una cuenta: lista, cambio de estado, alta y
// edicion. Habla con /api/v1/agreements/; quien puede editar lo decide el
// servidor (can_edit) y cada fila trae sus acciones.
import { apiGet, apiSend } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { formatDate, plain } from '#app/lib/format.js';

const STATUS = { open: 'Abierto', progress: 'En curso', done: 'Completado' };
const FIELDS = ['meeting_source', 'meeting_date', 'title', 'kind', 'due_date', 'status', 'notes'];
const HEADERS = ['Cuenta / acuerdo', 'Sesión', 'Prioridad / tipo', 'Situación / seguimiento', 'Acción / acuerdo', 'Compromiso', 'Estado', 'Acciones'];

/** @param {string} label @param {HTMLElement} control */
const field = (label, control) => el('label', {}, label, control);
/** @param {string} name @param {[string, string][]} options */
const select = (name, options) => el('select', { name }, ...options.map(([value, text]) => el('option', { value, text })));

/**
 * Con `account` la lista se limita a esa cuenta (solo pendientes abiertos); sin
 * ella muestra todas las del alcance, agrupadas, y la alta pide la cuenta.
 * @param {HTMLElement} container
 * @param {{account?: string, accounts?: string[]}} options
 */
export function mountAgreements(container, { account = '', accounts = [] }) {
  /** @type {any[]} */
  let items = [];
  let canEdit = false;
  /** @type {number | null} */
  let editing = null;

  const feedback = el('span', { id: 'agreement-feedback', role: 'status', 'aria-live': 'polite' });
  const search = /** @type {HTMLInputElement} */ (
    el('input', { type: 'search', id: 'agreement-search', placeholder: account ? 'Buscar pendiente o acuerdo…' : 'Buscar cuenta o acuerdo…', 'aria-label': 'Buscar decisiones, acuerdos o pendientes' })
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
  const body = el('tbody', { id: 'agreement-rows' });
  const add = /** @type {HTMLButtonElement} */ (el('button', { type: 'button', class: 'btn', id: 'agreement-new', hidden: true, text: '+ Agregar acuerdo o pendiente' }));
  const form = /** @type {HTMLFormElement} */ (
    el(
      'form',
      { id: 'agreement-form', class: 'agreement-form', hidden: true },
      ...(account
        ? []
        : [field('Cuenta', el('select', { name: 'account', required: true }, el('option', { value: '', text: 'Selecciona una cuenta' }), ...accounts.map((name) => el('option', { value: name, text: name }))))]),
      field('Origen', select('meeting_source', [['direction', 'Dirección'], ['board', 'Consejo']])),
      field('Fecha de sesión', el('input', { name: 'meeting_date', type: 'date', required: true })),
      field('Título', el('input', { name: 'title', maxlength: 200, required: true })),
      field('Tipo', select('kind', [['pending', 'Pendiente'], ['agreement', 'Acuerdo']])),
      field('Fecha compromiso', el('input', { name: 'due_date', type: 'date' })),
      field('Estado', select('status', Object.entries(STATUS))),
      field('Detalle / seguimiento', el('textarea', { name: 'notes', maxlength: 2000, rows: 2 })),
    )
  );
  const save = el('button', { type: 'submit', class: 'btn', text: 'Guardar' });
  const cancel = el('button', { type: 'button', class: 'btn btn-ghost', text: 'Cancelar', onclick: () => (form.hidden = true) });
  form.append(el('div', { class: 'agreement-form-actions' }, cancel, save));

  /** @param {string} message */
  const say = (message) => (feedback.textContent = message);
  /** @param {unknown} error */
  const reason = (error) => (error instanceof Error ? error.message : 'No se pudo completar la acción.');

  function draw() {
    const needle = plain(search.value);
    const shown = items
      .filter((x) => (!account || x.status !== 'done') && (!filter.value || x.status === filter.value) && plain([x.account, x.title, x.notes].join(' ')).includes(needle))
      .sort((a, b) => String(a.account || '~').localeCompare(String(b.account || '~')) || String(b.meeting_date || '').localeCompare(String(a.meeting_date || '')));
    let previous = null;
    body.replaceChildren(
      ...(shown.length
        ? shown.flatMap((item) => {
            const heading = !account && item.account !== previous ? [el('tr', { class: 'agreement-group' }, el('th', { colspan: HEADERS.length, scope: 'colgroup', text: item.account || 'Sin cuenta · pendiente de clasificar' }))] : [];
            previous = item.account;
            return [...heading, row(item)];
          })
        : [el('tr', {}, el('td', { colspan: HEADERS.length, text: 'Sin acuerdos de dirección o consejo registrados para esta búsqueda.' }))]),
    );
  }

  /** @param {any} item */
  function row(item) {
    const actions = item.actions || {};
    const state = /** @type {HTMLSelectElement} */ (
      el('select', { class: `agreement-status ${item.status}`, 'aria-label': `Cambiar estado de ${item.title}`, disabled: !actions.change_status }, ...Object.entries(STATUS).map(([value, text]) => el('option', { value, text })))
    );
    state.value = item.status;
    /** @param {string} status */
    const update = async (status) => {
      if (status === item.status) return;
      state.disabled = true;
      say('Guardando estado…');
      try {
        const { data } = await apiSend('PATCH', `agreements/${item.id}/`, { status });
        items = items.map((x) => (x.id === data.id ? data : x));
        say(status === 'done' ? 'Completado.' : 'Estado actualizado.');
        draw();
      } catch (error) {
        state.value = item.status;
        say(reason(error));
        state.disabled = false;
      }
    };
    state.addEventListener('change', () => update(state.value));
    const buttons = [];
    if (actions.edit) buttons.push(el('button', { type: 'button', class: 'btn btn-ghost', text: 'Editar', onclick: () => edit(item) }));
    if (actions.change_status && item.status !== 'done') {
      buttons.push(el('button', { type: 'button', class: 'btn btn-ghost', 'aria-label': `Completar ${item.title}`, text: 'Cerrar', onclick: () => update('done') }));
    }
    const session = item.meeting_date ? `${item.meeting_source === 'board' ? 'Consejo' : 'Dirección'} · ${formatDate(item.meeting_date)}` : 'Sesión pendiente de identificar';
    const cell = (/** @type {number} */ index, /** @type {...(Node|string)} */ ...children) => el('td', { dataset: { label: HEADERS[index] } }, ...children);
    return el(
      'tr',
      {},
      cell(0, item.title),
      cell(1, session),
      cell(2, item.kind === 'agreement' ? 'Acuerdo' : 'Pendiente'),
      cell(3, item.notes || '—'),
      cell(4, item.kind === 'agreement' ? 'Cumplir acuerdo' : 'Dar seguimiento'),
      cell(5, item.due_date ? formatDate(item.due_date) : 'Sin fecha'),
      cell(6, state),
      cell(7, ...buttons),
    );
  }

  /** @param {any} [item] */
  function edit(item) {
    form.reset();
    editing = item ? item.id : null;
    for (const name of [...FIELDS, 'account']) {
      const control = /** @type {HTMLInputElement | null} */ (form.elements.namedItem(name));
      if (control && item && item[name] != null) control.value = item[name];
    }
    form.hidden = false;
    /** @type {HTMLElement} */ (form.elements[0]).focus();
    say('');
  }

  add.addEventListener('click', () => edit());
  search.addEventListener('input', draw);
  filter.addEventListener('change', draw);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    /** @type {HTMLButtonElement} */ (save).disabled = true;
    const values = Object.fromEntries(new FormData(form));
    try {
      const { data } = editing === null ? await apiSend('POST', 'agreements/', { ...values, account: account || values.account }) : await apiSend('PATCH', `agreements/${editing}/`, values);
      items = editing === null ? [...items, data] : items.map((x) => (x.id === data.id ? data : x));
      form.hidden = true;
      say('Guardado.');
      draw();
    } catch (error) {
      say(reason(error));
    } finally {
      /** @type {HTMLButtonElement} */ (save).disabled = false;
    }
  });

  container.append(
    el(
      'section',
      { class: 'card agreements', id: 'executive-agreements', 'aria-labelledby': 'followup-title' },
      el('div', { class: 'agreements-heading' }, el('div', {}, el('h2', { id: 'followup-title', text: 'Decisiones y seguimiento' }), el('p', { class: 'note', text: account ? `Pendientes y acuerdos abiertos o en curso de ${account}.` : 'Acuerdos de sesiones de dirección y consejo, organizados por cuenta.' })), add),
      form,
      el('div', { class: 'cuenta-toolbar' }, search, filter, feedback),
      el('div', { class: 'cuenta-scroll' }, el('table', {}, el('thead', {}, el('tr', {}, ...HEADERS.map((h) => el('th', { scope: 'col', text: h })))), body)),
    ),
  );
  body.append(el('tr', {}, el('td', { colspan: HEADERS.length, text: 'Consultando acuerdos de dirección y consejo…' })));

  apiGet('agreements/', account ? { account, pending_only: 1 } : {})
    .then(({ data }) => {
      items = data.items;
      canEdit = data.can_edit;
      add.hidden = !canEdit;
      draw();
    })
    .catch((error) => {
      body.replaceChildren();
      say(error instanceof Error && error.message ? error.message : 'No se pudieron consultar los acuerdos. Intenta de nuevo.');
    });
}
