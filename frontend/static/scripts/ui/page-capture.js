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

/**
 * Agrega el boton de captura y su mensaje de estado.
 * @param {object} options
 * @param {HTMLElement} options.host Donde se colocan el boton y el estado.
 * @param {HTMLElement} options.target Lo que se captura.
 * @param {string} options.name Prefijo del archivo: <name>-AAAA-MM-DD.png
 * @param {string} options.libraryUrl Ruta de html2canvas.
 */
export function mountPageCapture({ host, target, name, libraryUrl }) {
  const button = /** @type {HTMLButtonElement} */ (
    el('button', { type: 'button', class: 'btn btn-ghost capture-button', 'data-html2canvas-ignore': 'true', text: '↓ Descargar captura' })
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
          clone.querySelectorAll('[hidden]').forEach((node) => node.remove());
          const style = doc.createElement('style');
          style.textContent =
            '*{animation:none!important;transition:none!important;caret-color:transparent!important}' +
            '[data-html2canvas-ignore]{display:none!important}';
          doc.head.appendChild(style);
        },
      });
      if (!canvas.width || !canvas.height) throw new Error('La captura está vacía. Vuelve a intentarlo.');
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
      if (!blob) throw new Error('No se pudo generar la imagen.');
      const now = new Date();
      const stamp = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
      const url = URL.createObjectURL(/** @type {Blob} */ (blob));
      const link = el('a', { href: url, download: `${name}-${stamp}.png` });
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
