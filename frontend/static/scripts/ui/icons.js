// @ts-check
// Iconos de trazo del portal. El markup es constante del modulo (nada viene
// del servidor), por eso se puede insertar como HTML.

const PATHS = {
  play: '<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4z"/>',
  pause: '<circle cx="12" cy="12" r="9"/><path d="M10 9v6M14 9v6"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
  people: '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2M17 4a4 4 0 0 1 0 7"/>',
  team: '<circle cx="9" cy="8" r="3"/><path d="M3 20v-2c0-5 12-5 12 0v2"/><circle cx="18" cy="9" r="2"/><path d="M18 15c3 0 4 2 4 5"/>',
  chart: '<path d="M3 3v18h18M7 16v-5M12 16V7M17 16v-8"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
};

/**
 * @param {keyof typeof PATHS} name
 * @param {number} [size]
 * @returns {SVGElement}
 */
export function icon(name, size = 24) {
  const holder = document.createElement('span');
  holder.innerHTML =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" ` +
    `stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${PATHS[name]}</svg>`;
  return /** @type {SVGElement} */ (holder.firstElementChild);
}
