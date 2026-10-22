// @ts-check
// Selector de periodo con calendario doble: rangos rapidos, pestanas por tipo
// de periodo y fechas manuales. Envia un formulario GET; el servidor valida el
// periodo (maximo tres anos) y la pagina lo lee de la URL.
import { calendarCells, iso, parseIso, quickRange, TAB_OF_PERIOD } from '#app/lib/date-range.js';
import { el } from '#app/lib/dom.js';

const QUICK = [
  ['today', 'Hoy'],
  ['yesterday', 'Ayer'],
  ['week', 'Esta semana'],
  ['seven', 'Últimos 7 días'],
  ['month', 'Este mes'],
  ['lastmonth', 'Último mes'],
  ['quarter', 'Este trimestre'],
  ['year', 'Este año'],
];
const TABS = [
  ['day', 'Día'],
  ['week', 'Semana'],
  ['month', 'Mes'],
  ['quarter', 'Trimestre'],
  ['year', 'Anual'],
  ['custom', 'Personalizado'],
];
const QUICK_TAB = /** @type {Record<string, string>} */ ({ today: 'day', yesterday: 'day', seven: 'custom', lastmonth: 'month' });
const MAX_DAYS = 1096;
const formatLong = (/** @type {string} */ key) => parseIso(key).toLocaleDateString('es-MX', { day: '2-digit', month: '2-digit', year: 'numeric' });

/**
 * @param {HTMLElement} container
 * @param {{label: string, start: string, end: string, today?: Date}} options start y end vienen del servidor (AAAA-MM-DD).
 */
export function mountPeriodPicker(container, { label, start, end, today = new Date() }) {
  const query = new URLSearchParams(location.search);
  const applied = /** @type {[string, string]} */ ([start, end]);
  const appliedMode = query.get('vista') || TAB_OF_PERIOD[query.get('periodo') || ''] || 'year';
  let mode = appliedMode;
  let base = parseIso(start);
  let choosingEnd = false;

  const from = /** @type {HTMLInputElement} */ (el('input', { type: 'date', name: 'desde', required: true }));
  const to = /** @type {HTMLInputElement} */ (el('input', { type: 'date', name: 'hasta', required: true }));
  const year = /** @type {HTMLSelectElement} */ (el('select', { 'aria-label': 'Año del calendario' }));
  const quarter = /** @type {HTMLSelectElement} */ (
    el('select', { 'aria-label': 'Trimestre' }, ...['T1 · Ene–Mar', 'T2 · Abr–Jun', 'T3 · Jul–Sep', 'T4 · Oct–Dic'].map((text, i) => el('option', { value: String(i + 1), text })))
  );
  const view = /** @type {HTMLInputElement} */ (el('input', { type: 'hidden', name: 'vista', value: mode }));
  const preview = el('strong', { 'aria-live': 'polite' });
  const error = el('span', { role: 'alert', class: 'picker-error' });
  const months = [el('div', { class: 'picker-month' }), el('div', { class: 'picker-month' })];
  const initialYear = parseIso(start).getFullYear();
  for (let y = Math.min(2000, initialYear); y <= Math.max(2100, initialYear); y++) year.append(el('option', { value: String(y), text: String(y) }));

  /** @type {Record<string, HTMLElement>} */
  const tabButtons = {};
  const quickButtons = /** @type {Record<string, HTMLElement>} */ ({});

  function paint() {
    preview.textContent = from.value ? `${formatLong(from.value)} - ${to.value ? formatLong(to.value) : '—'}` : 'Selecciona un rango';
    year.value = String(base.getFullYear());
    quarter.value = String(Math.floor(base.getMonth() / 3) + 1);
    view.value = mode;
    for (const [name, button] of Object.entries(tabButtons)) {
      button.classList.toggle('active', name === mode);
      button.setAttribute('aria-pressed', String(name === mode));
    }
    months.forEach((target, index) => {
      const month = new Date(base.getFullYear(), base.getMonth() + index, 1);
      const days = calendarCells(month.getFullYear(), month.getMonth()).map((cell) => {
        const inRange = Boolean(from.value && to.value && cell.key >= from.value && cell.key <= to.value);
        const edge = cell.key === from.value || cell.key === to.value;
        return el('button', {
          type: 'button',
          class: ['calendar-day', cell.outside && 'outside', cell.key === iso(today) && 'today', inRange && 'in-range', edge && 'boundary'].filter(Boolean).join(' '),
          text: String(cell.day),
          dataset: { date: cell.key },
          'aria-pressed': String(inRange || cell.key === from.value),
          'aria-label': parseIso(cell.key).toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
          tabindex: cell.outside ? -1 : 0,
        });
      });
      target.replaceChildren(
        el('h4', { text: month.toLocaleDateString('es-MX', { month: 'long', year: 'numeric' }) }),
        el('div', { class: 'calendar-grid' }, ...['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do'].map((d) => el('span', { class: 'calendar-weekday', text: d })), ...days),
      );
    });
  }

  /** @param {[string, string]} values @param {string} [next] */
  function setRange(values, next) {
    [from.value, to.value] = values;
    mode = next || mode;
    base = parseIso(from.value);
    choosingEnd = false;
    error.textContent = '';
    paint();
  }
  function reset() {
    setRange(applied, appliedMode);
    Object.values(quickButtons).forEach((b) => b.classList.remove('active'));
  }

  for (const [key, text] of QUICK) {
    quickButtons[key] = el('button', {
      type: 'button',
      text,
      onclick: () => {
        Object.entries(quickButtons).forEach(([name, b]) => b.classList.toggle('active', name === key));
        setRange(quickRange(key, today), QUICK_TAB[key] || key);
      },
    });
  }
  for (const [key, text] of TABS) {
    tabButtons[key] = el('button', {
      type: 'button',
      text,
      onclick: () => {
        Object.values(quickButtons).forEach((b) => b.classList.remove('active'));
        if (key === 'custom') {
          mode = key;
          choosingEnd = false;
          paint();
        } else setRange(quickRange(key, from.value ? parseIso(from.value) : today), key);
      },
    });
  }

  const calendars = el('div', { class: 'picker-calendars' }, el('button', { type: 'button', class: 'calendar-prev', 'aria-label': 'Mes anterior', text: '‹' }), months[0], months[1], el('button', { type: 'button', class: 'calendar-next', 'aria-label': 'Mes siguiente', text: '›' }));
  calendars.addEventListener('click', (event) => {
    const target = /** @type {HTMLElement} */ (event.target);
    if (target.closest('.calendar-prev')) return (base = new Date(base.getFullYear(), base.getMonth() - 1, 1)), paint();
    if (target.closest('.calendar-next')) return (base = new Date(base.getFullYear(), base.getMonth() + 1, 1)), paint();
    const key = /** @type {HTMLElement | null} */ (target.closest('[data-date]'))?.dataset.date;
    if (!key) return;
    if (mode !== 'custom') return setRange(quickRange(mode, parseIso(key)), mode);
    if (!choosingEnd) {
      from.value = key;
      to.value = '';
      choosingEnd = true;
    } else {
      const first = from.value;
      from.value = first < key ? first : key;
      to.value = first < key ? key : first;
      choosingEnd = false;
    }
    error.textContent = '';
    paint();
    /** @type {HTMLElement | null} */ (calendars.querySelector(`[data-date="${key}"]`))?.focus();
  });

  year.addEventListener('change', () => {
    base = new Date(Number(year.value), base.getMonth(), 1);
    if (['year', 'quarter', 'month'].includes(mode)) setRange(quickRange(mode, base), mode);
    else paint();
  });
  quarter.addEventListener('change', () => setRange(quickRange('quarter', new Date(Number(year.value), (Number(quarter.value) - 1) * 3, 1)), 'quarter'));
  for (const input of [from, to]) {
    input.addEventListener('input', () => {
      mode = 'custom';
      choosingEnd = false;
      error.textContent = '';
      if (from.value) base = parseIso(from.value);
      paint();
    });
  }

  const summary = el('summary', {}, el('span', { text: label }), el('span', { class: 'picker-chevron', 'aria-hidden': 'true', text: '⌄' }));
  const details = /** @type {HTMLDetailsElement} */ (el('details', { class: 'period-picker', id: 'period-picker' }, summary));
  const close = () => {
    reset();
    details.open = false;
    summary.focus();
  };
  const form = /** @type {HTMLFormElement} */ (
    el(
      'form',
      { method: 'get', id: 'period-form' },
      el('aside', { class: 'picker-shortcuts' }, el('h3', { text: 'Rangos rápidos' }), ...Object.values(quickButtons)),
      el(
        'div',
        { class: 'picker-main' },
        el('div', { class: 'picker-tabs', role: 'group', 'aria-label': 'Tipo de periodo' }, ...Object.values(tabButtons)),
        el('div', { class: 'picker-controls' }, el('label', {}, 'Año', year), el('label', {}, 'Trimestre', quarter), el('div', { class: 'picker-selected' }, el('span', { text: 'Rango seleccionado' }), preview)),
        calendars,
        el('div', { class: 'picker-manual' }, el('label', {}, 'Desde', from), el('label', {}, 'Hasta', to)),
        el('input', { type: 'hidden', name: 'periodo', value: 'rango' }),
        view,
        el(
          'div',
          { class: 'picker-actions' },
          error,
          el('button', { type: 'button', class: 'btn btn-ghost', text: 'Limpiar', onclick: () => ((from.value = to.value = ''), (mode = 'custom'), (choosingEnd = false), (error.textContent = ''), paint(), from.focus()) }),
          el('button', { type: 'button', class: 'btn btn-ghost', text: 'Cancelar', onclick: close }),
          el('button', { type: 'submit', class: 'btn', text: 'Aplicar periodo' }),
        ),
        el('p', { class: 'note', text: 'ⓘ Verifica Desde y Hasta antes de aplicar. Facturación según la fecha disponible en DataRevenue; costos y consumo por fecha de las horas. Base mensual pendiente de validar con Florencia.' }),
      ),
    )
  );
  form.addEventListener('submit', (event) => {
    if (!from.value || !to.value || from.value > to.value) {
      event.preventDefault();
      error.textContent = 'Selecciona una fecha inicial y una fecha final posterior.';
    } else if ((parseIso(to.value).getTime() - parseIso(from.value).getTime()) / 86400000 > MAX_DAYS) {
      event.preventDefault();
      error.textContent = 'El rango máximo es de tres años.';
    }
  });
  details.append(form);
  details.addEventListener('toggle', () => details.open && reset());
  document.addEventListener('keydown', (event) => event.key === 'Escape' && details.open && close());
  document.addEventListener('click', (event) => details.open && !details.contains(/** @type {Node} */ (event.target)) && (details.open = false));
  container.append(details);
  reset();
}
