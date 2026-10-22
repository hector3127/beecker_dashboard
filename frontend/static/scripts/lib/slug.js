// @ts-check
// Mismo criterio que apps/portal/services/slugs.build_slug: el nombre de una
// cuenta o de una persona se convierte en el texto que va en la direccion.

export const EMPTY_SLUG = 'sin-nombre';

/** "Clínica Sur" -> "clinica-sur". @param {string} name */
export function slugify(name) {
  const slug = name
    .normalize('NFKD')
    .replace(/[^\x00-\x7f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || EMPTY_SLUG;
}
