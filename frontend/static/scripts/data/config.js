// @ts-check
// Configuracion que el servidor entrega en <script id="app-config">.
// Es lo unico que cambia al montar el portal en otro lugar (por ejemplo Genesis).

/** @typedef {{apiBase: string, csrfCookie: string, loginUrl: string}} AppConfig */

/** @returns {AppConfig} */
function read() {
  const fallback = { apiBase: '/api/v1/', csrfCookie: 'csrftoken', loginUrl: '/' };
  const node = typeof document === 'undefined' ? null : document.getElementById('app-config');
  if (!node || !node.textContent) return fallback;
  try {
    return { ...fallback, ...JSON.parse(node.textContent) };
  } catch (_) {
    return fallback;
  }
}

export const config = Object.freeze(read());
