// @ts-check
// Busca el logo guardado de una cuenta. Solo cambia la presentacion: los
// nombres de origen y los permisos no se tocan.

/** @typedef {{account?: string, key?: string, url: string}} LogoItem */

/** Nombres que se muestran distinto pero abren la misma cuenta. */
const ALIASES = /** @type {Record<string, string>} */ ({
  'acs industires': 'acs industries',
  'atlas next wave': 'atlas nextwave',
  'grupo allen': 'grupo alen',
  'cadena comercial oxxo': 'oxxo',
  'heineken mexico': 'heineken',
});

/** Fuentes mensuales que traen solo la marca; reutilizan el logo guardado. */
const BRAND_LOGOS = /** @type {Record<string, string>} */ ({
  aeromexico: 'aeromexico cargo',
  nestle: 'nestle mexico',
  'arca continental': 'arca continental mexico',
});

/**
 * Nombre sin acentos, mayusculas, puntos finales ni espacios repetidos.
 * @param {unknown} value
 */
export function logoName(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
    .replace(/\.+$/, '')
    .trim()
    .replace(/\s+/g, ' ');
}

/** @param {unknown} value */
function canonical(value) {
  const name = logoName(value);
  return ALIASES[name] || name;
}

/**
 * @param {LogoItem[]} items Logos guardados.
 * @param {unknown} name Cuenta que se muestra.
 * @returns {LogoItem | undefined}
 */
export function findAccountLogo(items, name) {
  const exact = logoName(name);
  const itemName = (/** @type {LogoItem} */ item) => item.key || item.account;
  // OXXO y su nombre completo abren la misma cuenta.
  if (canonical(name) === 'oxxo') {
    const shared = items.find((item) => logoName(itemName(item)) === 'cadena comercial oxxo');
    if (shared) return shared;
  }
  // Primero el logo propio de la cuenta; despues los alias conocidos.
  const matched =
    items.find((item) => logoName(itemName(item)) === exact) ||
    items.find((item) => canonical(itemName(item)) === canonical(name));
  if (matched) return matched;
  // Nunca se reutiliza el logo de otra cuenta que no sea un alias explicito.
  const brand = BRAND_LOGOS[exact];
  return brand ? items.find((item) => logoName(itemName(item)) === brand) : undefined;
}
