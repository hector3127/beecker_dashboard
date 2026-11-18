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

/** @param {Document} doc @param {HTMLElement | null} clone */
function prepareCaptureContent(doc, clone) {
  if (!clone) return;
  clone.querySelectorAll('[hidden], dialog, [data-html2canvas-ignore]').forEach(node => node.remove());
  clone.querySelectorAll('details').forEach(details => {
    if (details.open && !details.matches('.executive-picker, .monthly-panel-info, .ranking-help, [data-capture-collapse]')) return;
    details.open = false;
    for (const child of [...details.childNodes]) {
      if (child.nodeType !== 1 || /** @type {Element} */ (child).tagName !== 'SUMMARY') child.remove();
    }
  });
  if (!doc.defaultView) return;
  clone.querySelectorAll('svg').forEach(root => {
    const size = root.getBoundingClientRect();
    if (size.width) root.setAttribute('width', String(size.width));
    if (size.height) root.setAttribute('height', String(size.height));
    for (const node of [root, ...root.querySelectorAll('*')]) {
      const computed = doc.defaultView.getComputedStyle(node);
      for (const attribute of ['color', 'fill', 'stroke', 'stop-color', 'stop-opacity', 'fill-opacity', 'stroke-opacity', 'opacity', 'stroke-width']) {
        const value = computed.getPropertyValue(attribute);
        if (!value) continue;
        if (value.includes('url(')) {
          const fragment = value.match(/#([^"')]+)["']?\)/);
          if (fragment) node.setAttribute(attribute, `url(#${fragment[1]})`);
        } else node.setAttribute(attribute, value);
      }
    }
  });
}

/** @param {Document} doc @param {HTMLElement | null} clone */
async function rasterizeCaptureIcons(doc, clone) {
  if (!clone || !doc.defaultView) return;
  const icons = clone.querySelectorAll('svg.metric-visual, svg.metric-gauge, svg.executive-card-art');
  await Promise.all([...icons].map(async icon => {
    const bounds = icon.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    const standalone = /** @type {SVGElement} */ (icon.cloneNode(true));
    for (const node of [standalone, ...standalone.querySelectorAll('*')]) node.removeAttribute('style');
    const source = new XMLSerializer().serializeToString(standalone);
    const bitmap = new Image();
    await new Promise((resolve, reject) => {
      bitmap.onload = resolve;
      bitmap.onerror = () => reject(new Error('No se pudo preparar un icono para la captura.'));
      bitmap.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(source)}`;
    });
    const canvas = doc.createElement('canvas');
    for (const attribute of icon.attributes) {
      if (attribute.name !== 'style') canvas.setAttribute(attribute.name, attribute.value);
    }
    canvas.width = Math.ceil(bounds.width * 2);
    canvas.height = Math.ceil(bounds.height * 2);
    const context = canvas.getContext('2d');
    if (!context) throw new Error('No se pudo preparar la captura.');
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    icon.replaceWith(canvas);
  }));
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
        onclone: async (/** @type {Document} */ doc) => {
          const clone = /** @type {HTMLElement} */ (doc.getElementById(target.id));
          prepareCaptureContent(doc, clone);
          const style = doc.createElement('style');
          const nonce = /** @type {HTMLScriptElement | null} */ (document.querySelector('script[nonce]'))?.nonce;
          if (nonce) style.nonce = nonce;
          style.textContent =
            '*{animation:none!important;transition:none!important;caret-color:transparent!important}' +
            '[data-html2canvas-ignore]{display:none!important}';
          doc.head.appendChild(style);
          normalizeCaptureColors(doc);
          await rasterizeCaptureIcons(doc, clone);
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
if (typeof document !== 'undefined' && !document.querySelector('[data-page-capture="off"]')) {
  const entry = /** @type {HTMLScriptElement | null} */ (document.querySelector('script[data-auto-page-capture]'));
  const target = document.getElementById('main-content');
  let host = document.getElementById('executive-capture-actions') || document.getElementById('ops-actions') || document.querySelector('.top .fresh');
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
