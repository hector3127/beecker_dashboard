// @ts-check
// Descarga la pantalla actual como PNG sin volver a pedir sus datos.
// La libreria html2canvas se carga solo cuando alguien pide la captura.
import { el } from '#app/lib/dom.js';

/** @param {string} url @returns {Promise<(node: HTMLElement, options: object) => Promise<HTMLCanvasElement>>} */
function loadLibrary(url) {
  const existing = /** @type {any} */ (window).html2canvas;
  if (typeof existing === 'function') return Promise.resolve(existing);
  return new Promise((resolve, reject) => {
    const tag = document.createElement('script');
    tag.src = url;
    tag.onload = () => {
      const library = /** @type {any} */ (window).html2canvas;
      if (typeof library === 'function') resolve(library);
      else reject(new Error('No se pudo iniciar la captura.'));
    };
    tag.onerror = () => {
      tag.remove();
      reject(new Error('No se pudo cargar la captura. Vuelve a intentarlo.'));
    };
    document.head.appendChild(tag);
  });
}

/** Escala que mantiene la imagen dentro de los limites de los navegadores. */
export function captureScale(width, height) {
  return Math.min(
    2,
    16000 / Math.max(width, 1),
    30000 / Math.max(height, 1),
    Math.sqrt(45000000 / Math.max(width * height, 1)),
  );
}

/** Convert CSS Color 4 values in the clone to colors html2canvas supports. */
function normalizeCaptureColors(doc) {
  const canvas = doc.createElement('canvas');
  canvas.width = canvas.height = 1;
  const context = canvas.getContext('2d', { willReadFrequently: true });
  if (!context || !doc.defaultView) return;
  const normalize = (value) => {
    const pattern = /(?:color-mix|color|oklch|oklab|lch|lab|hwb)\(/g;
    let match;
    let output = '', previous = 0;
    while ((match = pattern.exec(value))) {
      let depth = 1, end = pattern.lastIndex;
      while (end < value.length && depth) {
        if (value[end] === '(') depth++;
        else if (value[end] === ')') depth--;
        end++;
      }
      if (depth) break;
      context.clearRect(0, 0, 1, 1);
      context.fillStyle = value.slice(match.index, end);
      context.fillRect(0, 0, 1, 1);
      const [r, g, b, a] = context.getImageData(0, 0, 1, 1).data;
      output += value.slice(previous, match.index) + `rgba(${r},${g},${b},${a / 255})`;
      previous = end;
      pattern.lastIndex = end;
    }
    return output + value.slice(previous);
  };
  const properties = ['color', 'background-color', 'background-image', 'box-shadow', 'text-shadow',
    'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
    'outline-color', 'text-decoration-color', 'fill', 'stroke', 'stop-color'];
  doc.querySelectorAll('*').forEach((element) => {
    if (!element.style) return;
    const computed = doc.defaultView.getComputedStyle(element);
    for (const property of properties) {
      const value = computed.getPropertyValue(property);
      if (/(?:color-mix|color|oklch|oklab|lch|lab|hwb)\(/.test(value)) {
        element.style.setProperty(property, normalize(value), 'important');
      }
    }
  });
}

/**
 * Agrega el boton de captura y su mensaje de estado.
 * @param {object} options
 * @param {HTMLElement} options.host Donde se colocan el boton y el estado.
 * @param {HTMLElement} options.target Lo que se captura.
 * @param {string | (() => string)} options.name Prefijo del archivo: <name>-AAAA-MM-DD.png
 * @param {string} options.libraryUrl Ruta de html2canvas.
 */
export function mountPageCapture({ host, target, name, libraryUrl }) {
  if (!host || !target || !libraryUrl) return;
  // Shared layouts and page scripts must never create duplicate controls.
  if (document.querySelector(`.capture-button[data-capture-target="${target.id}"]`)) return;
  const button = /** @type {HTMLButtonElement} */ (
    el('button', { type: 'button', class: 'btn btn-ghost capture-button', 'data-html2canvas-ignore': 'true', 'data-capture-target': target.id, text: '↓ Descargar captura' })
  );
  const status = el('span', { class: 'capture-status', role: 'status', 'data-html2canvas-ignore': 'true' });
  host.append(button, status);

  button.addEventListener('click', async () => {
    button.disabled = true;
    button.textContent = 'Generando captura…';
    status.textContent = '';
    try {
      const capture = await loadLibrary(libraryUrl);
      if (document.fonts) await document.fonts.ready;
      const width = Math.ceil(target.scrollWidth);
      const height = Math.ceil(target.scrollHeight);
      const canvas = await capture(target, {
        backgroundColor: getComputedStyle(document.body).backgroundColor,
        scale: captureScale(width, height),
        useCORS: true,
        allowTaint: false,
        logging: false,
        windowWidth: window.innerWidth,
        scrollX: 0,
        scrollY: 0,
        onclone: (/** @type {Document} */ doc) => {
          const clone = /** @type {HTMLElement} */ (doc.getElementById(target.id));
          clone?.querySelectorAll('[hidden], dialog:not([open])').forEach((node) => node.remove());
          const style = doc.createElement('style');
          style.textContent =
            '*{animation:none!important;transition:none!important;caret-color:transparent!important}' +
            '[data-html2canvas-ignore]{display:none!important}';
          doc.head.appendChild(style);
          normalizeCaptureColors(doc);
        },
      });
      if (!canvas.width || !canvas.height) throw new Error('La captura está vacía. Vuelve a intentarlo.');
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
      if (!blob) throw new Error('No se pudo generar la imagen.');
      const now = new Date();
      const stamp = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
      const url = URL.createObjectURL(/** @type {Blob} */ (blob));
      const link = el('a', { href: url, download: `${typeof name === 'function' ? name() : name}-${stamp}.png` });
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status.textContent = 'Captura descargada.';
    } catch (error) {
      status.textContent = error instanceof Error && error.message ? error.message : 'No se pudo generar la captura.';
    } finally {
      button.disabled = false;
      button.textContent = '↓ Descargar captura';
    }
  });
}


/** Stable, readable filenames for every dashboard screen. */
export function captureName(path, title) {
  const names = { '/': 'business-overview', '/operativa/': 'operativa', '/comercial/': 'comercial' };
  if (names[path]) return names[path];
  return (title || path || 'dashboard').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 100) || 'dashboard';
}

// Both the modular layout and the remaining previous views use this entry.
if (typeof document !== 'undefined') {
  const entry = /** @type {HTMLScriptElement | null} */ (document.querySelector('script[data-auto-page-capture]'));
  const target = document.getElementById('main-content');
  let host = document.getElementById('ops-actions') || document.querySelector('.top .fresh');
  // Some previous screens intentionally hide their freshness block.
  if (entry && target && (!host || !host.getClientRects().length)) {
    const header = document.querySelector('header.top');
    if (header) {
      host = el('div', { class: 'page-capture-actions' });
      header.append(host);
    }
  }
  if (entry && target && host) {
    mountPageCapture({
      host: /** @type {HTMLElement} */ (host), target,
      name: () => captureName(location.pathname, document.title),
      libraryUrl: entry.dataset.captureLibrary || '',
    });
  }
}
