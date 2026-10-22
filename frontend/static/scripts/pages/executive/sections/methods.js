// @ts-check
// «Fuentes y calculo» de cada tarjeta: las definiciones salen del diccionario
// de datos (la misma fuente que el glosario), no se repiten aqui.
import { el } from '#app/lib/dom.js';
import { openDetail } from '#app/ui/detail-dialog.js';

/**
 * @param {{groups: any[], concepts: any[]}} reference Respuesta de reference/glossary.
 * @param {string} groupName Financiera, Operaciones o Comercial.
 * @param {string} dictionaryUrl
 */
export function openMethod(reference, groupName, dictionaryUrl) {
  const group = reference.groups.find((g) => g.name === groupName);
  const body = openDetail(`Fuentes y cálculo · ${groupName}`);
  const byName = new Map(reference.concepts.map((c) => [c.name, c]));
  for (const item of group ? group.terms : []) {
    const concept = byName.get(item.concept);
    body.append(el('article', { class: 'method' }, el('h3', { text: item.term }), el('p', { text: concept ? concept.definition : item.summary }), ...(concept ? [el('p', { class: 'note', text: `Fuente / validación: ${concept.source}` })] : [])));
  }
  body.append(el('p', {}, el('a', { href: dictionaryUrl, text: 'Abrir glosario completo' })));
}
