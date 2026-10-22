// @ts-check
// Glosario desplegable por grupos. Los textos llegan de la API (diccionario
// de datos); este componente solo los dibuja.
import { el } from '#app/lib/dom.js';

/**
 * @param {HTMLElement} container
 * @param {{name: string, terms: {term: string, summary: string}[]}[]} groups
 * @param {string} dictionaryUrl
 */
export function mountGlossary(container, groups, dictionaryUrl) {
  container.replaceChildren(
    el(
      'details',
      { class: 'glossary' },
      el('summary', {}, el('span', { text: '¿Qué significa cada indicador?' }), el('span', { class: 'glossary-hint', text: 'Consultar glosario' })),
      el('div', { class: 'glossary-grid' }, ...groups.map((g) => el('section', {}, el('h2', { text: g.name }), el('dl', {}, ...g.terms.flatMap((t) => [el('dt', { text: t.term }), el('dd', { text: t.summary })]))))),
      el(
        'footer',
        {},
        el('p', {}, el('strong', { text: '* Parcial:' }), ' faltan datos para completar el indicador. ', el('strong', { text: 'Pendiente:' }), ' no hay información suficiente; no equivale a cero.'),
        el('a', { class: 'btn btn-ghost', href: dictionaryUrl, text: 'Ver fórmulas, fuentes y validaciones' }),
      ),
    ),
  );
}
