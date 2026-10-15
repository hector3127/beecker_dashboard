/* Preserve the immediate parent, including its own return chain. */
(function () {
  'use strict';
  const targets = /^\/(?:cuenta\/[^/]+\/|proyectos\/[^/]+\/|ejecutiva\/costos\/detalle\/)$/;
  document.addEventListener('click', function (event) {
    const link = event.target.closest('a[href]');
    if (!link || link.hasAttribute('data-portal-back') || link.classList.contains('cost-back')) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || !targets.test(url.pathname)) return;
    const source = new URL(location.href);
    if (source.searchParams.has('periodo') && !url.searchParams.has('periodo')) {
      for (const key of ['periodo', 'anio', 'mes', 'trimestre', 'desde', 'hasta']) {
        if (source.searchParams.has(key)) url.searchParams.set(key, source.searchParams.get(key));
      }
    }
    url.searchParams.set('volver', location.pathname + location.search + location.hash);
    link.href = url.href;
  });
  // Restore the account list's client filters when a detail links back to it.
  if (location.pathname !== '/ejecutiva/cuentas/') return;
  const search = document.getElementById('account-search');
  const filter = document.getElementById('account-filter');
  if (!search || !filter) return;
  const params = new URLSearchParams(location.search);
  search.value = params.get('buscar') || '';
  filter.value = params.get('clasificacion') || '';
  search.dispatchEvent(new Event('input', {bubbles: true}));
  function save() {
    const url = new URL(location.href);
    for (const [key, value] of [['buscar', search.value], ['clasificacion', filter.value]]) {
      if (value) url.searchParams.set(key, value); else url.searchParams.delete(key);
    }
    history.replaceState(history.state, '', url.pathname + url.search + url.hash);
  }
  search.addEventListener('input', save);
  filter.addEventListener('change', save);
})();
