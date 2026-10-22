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
