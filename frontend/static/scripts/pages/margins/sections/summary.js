// @ts-check
// Metodologia y los cinco promedios de la comparativa de margenes.
import { el, svg } from '#app/lib/dom.js';


/** Iconos de la comparativa, sin imágenes externas. @param {string} kind */
export function marginIcon(kind) {
  const paths = {
    info: ['M12 11v6M12 7v1', 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
    sigma: ['M19 4H5l7 8-7 8h14'],
    scope: ['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8', 'M9 3h6l1 3 3 1 2 5-2 2-1 4-4 3-2-2-4-1-3-4 2-2 1-4Z'],
    list: ['M4 5h16M4 12h16M4 19h16', 'M4 8h11M4 15h11M4 22h11'],
    percent: ['M6 18 18 6', 'M8 6a2 2 0 1 0-4 0 2 2 0 0 0 4 0', 'M20 18a2 2 0 1 0-4 0 2 2 0 0 0 4 0'],
    bars: ['M4 20V11h4v9zM10 20V6h4v14zM16 20V3h4v17z'],
    warning: ['M12 3 2 21h20L12 3Z', 'M12 9v5M12 17v1'],
    clock: ['M12 7v5h5', 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
    coins: ['M3 8c0 3 12 3 12 0S3 5 3 8Zm0 0v9c0 3 12 3 12 0V8', 'M3 12c0 3 12 3 12 0M3 16c0 3 12 3 12 0', 'M10 4c0 3 12 3 12 0S10 1 10 4Zm12 0v9c0 2-4 3-7 2M15 8c4 1 7 0 7-1'],
    account: ['M5 21V3h14v18M3 21h18M9 21v-5h6v5M8 7h2M14 7h2M8 11h2M14 11h2'],
    document: ['M6 3h8l4 4v14H6V3ZM14 3v5h4M9 12h6M9 16h6'],
    search: ['M21 21l-6-6', 'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0'],
  };
  return svg('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.8', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' }, ...(paths[kind] || paths.bars).map(d => svg('path', { d })));
}

/** @param {number | null | undefined} value @param {string} [unit] */
const oneDecimal = (value, unit = '%') =>
  value === null || value === undefined ? 'Pendiente' : `${value.toFixed(1)}${unit}`;

/** @param {string} symbol @param {string} className @param {Node[]} body */
const metric = (symbol, className, body) =>
  el(
    'article',
    { class: className },
    el('span', { class: 'summary-symbol', 'aria-hidden': 'true' }, marginIcon(symbol)),
    el('div', {}, ...body),
  );

/** Titulo con salto de linea: "Margen real<br>promedio". @param {string} first @param {string} [second] */
const heading = (first, second) => el('h2', {}, first, ...(second ? [el('br'), second] : []));

/** @param {string} excluded */
export function renderMethod(excluded) {
  const paragraph = (text) => el('p', { text });
  const bullets = (items) => el('ul', {}, ...items.map(text => el('li', { text })));
  const card = (title, icon, className, ...body) => el('section', {
    class: `method-info-card ${className}`,
  }, el('span', { class: 'method-card-icon', 'aria-hidden': 'true' }, marginIcon(icon)),
  el('div', { class: 'method-card-body' }, el('h3', { text: title }), ...body));
  return el('details', { class: 'opportunity-card opportunity-method' },
    el('summary', {},
      el('span', { class: 'summary-symbol', 'aria-hidden': 'true' }, marginIcon('coins')),
      el('span', { class: 'method-heading' },
        el('strong', { text: 'Bookings, operación y cobranza' }),
        el('span', { class: 'method-subtitle', text: 'Información sobre el cálculo y alcance de los bookings, operación y cobranza en esta vista.' }))),
    el('div', { class: 'opportunity-method-content method-info-grid' },
      card('Qué representa', 'bars', 'method-represents',
        paragraph('Bookings: suma de la columna H de DataRevenue para la oportunidad, únicamente dentro del rango seleccionado en Business Overview, según Fecha Revenue Ajustado (columna G).')),
      card('Qué incluye', 'list', 'method-includes', bullets([
        'Bookings: Confirmed, Invoiced y Collected, incluyendo Factoring.',
        'Facturado: Invoiced y Collected, incluyendo Factoring.',
        'Cobrado: Collected y Collected Factoring.',
        'Todos estos importes usan la fecha G de DataRevenue dentro del rango elegido.',
      ])),
      card('Alcance', 'scope', 'method-scope',
        paragraph('Servicios excluidos de esta vista:'),
        el('div', { class: 'method-service-tags', 'aria-label': 'Servicios excluidos de esta comparativa' },
          ...['Licencias', 'SaaS', 'Servicios especializados'].map(text => el('span', { text }))),
        paragraph(`Solo en esta comparativa se excluyen ${(excluded || 'Licencias, SaaS y servicios especializados').toLowerCase()}. Las demás vistas conservan su alcance.`)),
      card('Margen vendido y real', 'sigma', 'method-margins',
        paragraph('Vendido: columna I de DataRevenue.'),
        paragraph('Real: (revenue del periodo − costos) ÷ revenue del periodo, en %.'),
        paragraph('Se conserva la base G/H, incluyendo Confirmed. No se usa Cobrado como denominador.')),
      card('Desviación', 'percent', 'method-deviation',
        paragraph('Margen real − margen vendido, en puntos porcentuales (pp).')),
      card('Notas importantes', 'info', 'method-notes', bullets([
        'Revenue operado usa provisionalmente Fecha Revenue Ajustado (G) como fecha del servicio, dentro del rango y hasta hoy. Esta equivalencia está por validar con Florencia.',
        'Los estados de facturación y cobranza no acreditan por sí solos la fecha de factura o transferencia bancaria.',
        'Costos: horas de Clockify × tarifa interna de banda, incluidas horas no facturables y sin task. * Costos parciales: el margen puede variar.',
        'Los IDs compartidos muestran una referencia con su costo disponible total, marcada con *. No es una asignación exclusiva ni se suma entre oportunidades; estas referencias se excluyen de los promedios de margen real y desviación.',
        'En los totales de cuenta, los costos se cuentan una sola vez por registro de horas. El margen vendido de la cuenta se pondera por revenue de las oportunidades con dato disponible.',
        'Cifras monetarias en dólares estadounidenses: K = miles · M = millones · B = mil millones.',
      ])),
    ),
  );
}

/** @param {any} summary */
export function renderSummary(summary) {
  const deviation = summary.deviation;
  const tone = deviation < 0 ? 'bad' : deviation > 0 ? 'good' : '';
  const verdict = deviation < 0 ? 'Por debajo del margen' : deviation > 0 ? 'Por encima del margen' : 'Comparativa disponible';
  const metrics = el(
    'section',
    { class: 'opportunity-metrics', 'aria-label': 'Resumen de oportunidades' },
    metric('list', '', [
      heading('Oportunidades', 'con costos completos'),
      el('strong', { text: `${summary.complete} de ${summary.total}` }),
      el('small', { text: `${summary.complete_pct.toFixed(1)}% del total` }),
    ]),
    metric('percent', 'metric-green', [
      heading('Margen vendido', 'promedio'),
      el('strong', { text: oneDecimal(summary.sold) }),
      el('small', { text: `${summary.sold_count} oportunidades con margen` }),
    ]),
    metric('bars', '', [
      heading('Margen real', 'promedio'),
      el('strong', { text: oneDecimal(summary.actual) }),
      el('small', { text: `${summary.actual_count} con costos disponibles · incluye parciales` }),
    ]),
    metric('warning', 'metric-deviation', [
      heading('Desviación promedio'),
      el('strong', { class: tone, text: oneDecimal(deviation, ' pp') }),
      el('small', { text: `${verdict} · ${summary.deviation_count} oportunidades` }),
    ]),
    metric('clock', 'metric-pending', [
      heading('Pendientes de costo'),
      el('strong', { text: summary.pending }),
      el('small', { text: `${summary.pending_pct.toFixed(1)}% del total` }),
    ]),
  );
  return [metrics];
}
