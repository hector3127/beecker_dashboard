// @ts-check
// Cliente de la API v1: una sola puerta para pedir datos y enviar acciones.
// Las pantallas no llaman a fetch directo; asi los errores, la sesion y el
// CSRF se manejan igual en todas.
import { config } from '#app/data/config.js';

const TIMEOUT_MS = 60000;

/** Error de la API con el formato que usan las pantallas. */
export class ApiError extends Error {
  /**
   * @param {number} status Codigo HTTP; 0 si no hubo respuesta.
   * @param {string} code Clave estable: unauthenticated, forbidden, not_found, timeout, network...
   * @param {string} message Texto para la persona.
   * @param {Record<string, string[]>} [fields] Errores por campo en formularios.
   */
  constructor(status, code, message, fields) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

/** Token que Django dejo en la cookie; las escrituras lo envian en el encabezado. */
function csrfToken() {
  const prefix = config.csrfCookie + '=';
  const found = document.cookie.split(';').map((part) => part.trim()).find((part) => part.startsWith(prefix));
  return found ? decodeURIComponent(found.slice(prefix.length)) : '';
}

const BY_STATUS = {
  401: ['unauthenticated', 'Tu sesión terminó. Vuelve a iniciar sesión.'],
  403: ['forbidden', 'No tienes acceso a esta información.'],
  404: ['not_found', 'No se encontró lo que buscas.'],
};

/**
 * Traduce una respuesta con error al ApiError que ven las pantallas.
 * @param {Response} response
 */
async function failure(response) {
  let body = null;
  try {
    body = await response.json();
  } catch (_) {
    /* Respuesta sin JSON, por ejemplo la pagina 502 del servidor. */
  }
  const known = BY_STATUS[/** @type {401|403|404} */ (response.status)];
  const error = body && typeof body === 'object' ? body.error : null;
  if (error && error.code) {
    return new ApiError(response.status, error.code, error.message || '', error.fields);
  }
  if (known) return new ApiError(response.status, known[0], known[1]);
  if (response.status >= 500) {
    return new ApiError(response.status, 'server', 'El servidor no pudo completar la consulta. Intenta de nuevo.');
  }
  const detail = body && typeof body.detail === 'string' ? body.detail : 'No se pudo completar la solicitud.';
  return new ApiError(response.status, 'request', detail);
}

/**
 * @param {string} method
 * @param {string} path Ruta relativa a la raiz de la API, por ejemplo "ping/".
 * @param {{params?: Record<string, unknown>, body?: unknown, signal?: AbortSignal, timeout?: number}} [options]
 * @returns {Promise<any>} El cuerpo JSON completo: {data, meta}.
 */
async function request(method, path, options = {}) {
  const url = new URL(config.apiBase + path, location.origin);
  for (const [key, value] of Object.entries(options.params || {})) {
    if (Array.isArray(value)) for (const item of value) url.searchParams.append(key, String(item));
    else if (value !== null && value !== undefined && value !== '') url.searchParams.set(key, String(value));
  }
  const headers = /** @type {Record<string, string>} */ ({ Accept: 'application/json' });
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json';
    headers['X-CSRFToken'] = csrfToken();
  }
  const timer = new AbortController();
  const timeout = setTimeout(() => timer.abort(), options.timeout ?? TIMEOUT_MS);
  const signals = options.signal ? [options.signal, timer.signal] : [timer.signal];
  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      credentials: 'same-origin',
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: AbortSignal.any(signals),
    });
  } catch (error) {
    // Una pantalla que cancela su propia peticion no necesita mensaje.
    if (options.signal?.aborted) throw error;
    if (timer.signal.aborted) throw new ApiError(0, 'timeout', 'La consulta tardó demasiado. Intenta de nuevo.');
    throw new ApiError(0, 'network', 'No hubo conexión con el servidor.');
  } finally {
    clearTimeout(timeout);
  }
  // Una sesion vencida redirige al login: llega HTML, no JSON.
  const type = response.headers.get('content-type') || '';
  if (response.redirected && !type.includes('json')) {
    throw new ApiError(401, ...BY_STATUS[401]);
  }
  if (!response.ok) throw await failure(response);
  try {
    return await response.json();
  } catch (_) {
    throw new ApiError(response.status, 'invalid_response', 'La respuesta del servidor no es válida.');
  }
}

/** @type {(path: string, params?: Record<string, unknown>, options?: {signal?: AbortSignal, timeout?: number}) => Promise<any>} */
export const apiGet = (path, params, options) => request('GET', path, { ...options, params });

/** @type {(method: 'POST'|'PATCH'|'PUT'|'DELETE', path: string, body?: unknown, options?: {signal?: AbortSignal, timeout?: number}) => Promise<any>} */
export const apiSend = (method, path, body, options) => request(method, path, { ...options, body });
