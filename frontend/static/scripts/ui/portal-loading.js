// @ts-check
// Esqueleto y rueda de carga para los textos «Cargando…», «Consultando…» y
// similares, y para toda la pagina al navegar. Un dato «Pendiente» nunca se
// toma por carga.

/** @param {unknown} text */
export const isLoadingMessage = (text) => {
  const value = String(text || '').trim();
  return /^(?:cargando|consultando|calculando|preparando|actualizando|guardando)(?:\s|[.…:]|$)/i.test(value) && String(text || '').length < 220;
};

const counters = new WeakMap();

/**
 * Marca una region como cargando hasta que se llame a lo que devuelve.
 * @param {HTMLElement | null} target
 */
export function beginLoading(target) {
  if (!target) return () => {};
  counters.set(target, (counters.get(target) || 0) + 1);
  target.classList.add('portal-loading-region');
  target.setAttribute('aria-busy', 'true');
  let finished = false;
  return () => {
    if (finished) return;
    finished = true;
    const count = Math.max(0, (counters.get(target) || 1) - 1);
    counters.set(target, count);
    if (!count) {
      target.classList.remove('portal-loading-region');
      target.setAttribute('aria-busy', 'false');
    }
  };
}

/** @param {Element | null} element */
function inspect(element) {
  if (!element?.matches || element.closest('script,style,svg,button,a,select,textarea,.metric-loading,[contenteditable]')) return;
  if (element.childElementCount !== 0) {
    element.classList.remove('portal-loading-message');
    return;
  }
  element.classList.toggle('portal-loading-message', isLoadingMessage(element.textContent));
}

/** @param {Node} root */
function scan(root) {
  if (root.nodeType === 3) {
    inspect(root.parentElement);
    return;
  }
  inspect(/** @type {Element} */ (root));
  /** @type {Element} */ (root).querySelectorAll?.('*').forEach(inspect);
}

/** Observa el contenido principal y marca los mensajes de carga. */
export function watchLoadingMessages() {
  const content = document.getElementById('main-content');
  if (!content) return;
  scan(content);
  new MutationObserver((changes) => {
    for (const change of changes) {
      if (change.type === 'characterData') scan(change.target);
      else {
        inspect(/** @type {Element} */ (change.target));
        change.addedNodes.forEach(scan);
      }
    }
  }).observe(content, { subtree: true, childList: true, characterData: true });
  /** @type {(() => void) | null} */
  let endNavigation = null;
  addEventListener('beforeunload', () => {
    endNavigation = beginLoading(content);
  });
  addEventListener('pageshow', () => {
    endNavigation?.();
    endNavigation = null;
  });
}
