// @ts-check
// Fuentes y calculo de cada indicador, en un panel que no cambia la altura de las tarjetas.

const LABELS = /** @type {Record<string, string>} */ ({ financial: 'Financiera', operations: 'Operaciones', commercial: 'Comercial' });

export function mountMethods() {
  const drawer = /** @type {HTMLDialogElement | null} */ (document.getElementById('executive-method-dialog'));
  if (!drawer) return;
  const panels = [...drawer.querySelectorAll('[data-method-panel]')];
  /** @type {HTMLElement | null} */
  let trigger = null;
  document.querySelectorAll('[data-method]').forEach((node) =>
    node.addEventListener('click', () => {
      const button = /** @type {HTMLElement} */ (node);
      const kind = button.dataset.method || '';
      if (!LABELS[kind]) return;
      trigger = button;
      for (const panel of panels) /** @type {HTMLElement} */ (panel).hidden = /** @type {HTMLElement} */ (panel).dataset.methodPanel !== kind;
      /** @type {HTMLElement} */ (document.getElementById('method-context')).textContent = LABELS[kind];
      /** @type {HTMLElement} */ (drawer.querySelector('.method-drawer-body')).scrollTop = 0;
      document.documentElement.classList.add('portal-modal-open');
      drawer.showModal();
    }),
  );
  drawer.querySelectorAll('[data-method-close]').forEach((button) => button.addEventListener('click', () => drawer.close()));
  drawer.addEventListener('close', () => {
    document.documentElement.classList.remove('portal-modal-open');
    trigger?.focus({ preventScroll: true });
  });
}
