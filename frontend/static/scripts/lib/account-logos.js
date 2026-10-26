// @ts-check
// Catalogo de logos de cuenta: una sola lectura por carga de pagina, compartida
// por todas las pantallas. Si falla, la pantalla se queda con las iniciales.
import { apiGet } from '#app/data/api-client.js';

export { findAccountLogo, logoName } from '#app/lib/account-logo-lookup.js';

/** @typedef {{account: string, key: string, url: string}} AccountLogo */
/** @typedef {{items: AccountLogo[], can_edit: boolean}} AccountLogoCatalog */

/** @type {Promise<AccountLogoCatalog> | null} */
let catalog = null;

/**
 * Lee el catalogo completo (incluye si la persona puede editar).
 * Una lectura fallida no se guarda para poder reintentar.
 * @returns {Promise<AccountLogoCatalog>}
 */
export function loadAccountLogoCatalog() {
  if (!catalog) {
    catalog = apiGet('account-logos/').then(({ data }) => data);
    catalog.catch(() => {
      catalog = null;
    });
  }
  return catalog;
}

/**
 * Solo los logos, sin lanzar error: lista vacia si no se pudieron leer.
 * @returns {Promise<AccountLogo[]>}
 */
export async function loadAccountLogos() {
  try {
    return (await loadAccountLogoCatalog()).items || [];
  } catch (_) {
    return [];
  }
}

/** Descarta el catalogo guardado, por ejemplo despues de subir o borrar un logo. */
export function resetAccountLogos() {
  catalog = null;
}
