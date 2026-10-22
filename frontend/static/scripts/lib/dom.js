// @ts-check
// Crea nodos sin innerHTML: el texto entra siempre como texto, nunca como HTML.

/**
 * @param {string} tag
 * @param {Record<string, any>} [props] class, text, dataset, onclick... el resto va como atributo.
 * @param {...(Node|string)} children
 * @returns {HTMLElement}
 */
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'dataset') Object.assign(node.dataset, value);
    else if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : String(value));
  }
  node.append(...children);
  return node;
}

const SVG_NS = 'http://www.w3.org/2000/svg';

/**
 * Crea un nodo SVG con atributos; igual que `el`, pero en el espacio de nombres SVG.
 * @param {string} tag
 * @param {Record<string, any>} [attrs]
 * @param {...(Node|string)} children
 * @returns {SVGElement}
 */
export function svg(tag, attrs = {}, ...children) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value !== undefined && value !== null && value !== false) node.setAttribute(key, String(value));
  }
  node.append(...children);
  return node;
}

