// Conserva los datos y filtros visibles mientras prepara un nuevo corte.
(async function () {
  const state = document.getElementById('cached-page-state');
  if (!state) return;
  const url = new URL(window.location.href);
  url.searchParams.set('actualizar', '1');
  try {
    const response = await fetch(url, {credentials: 'same-origin'});
    if (!response.ok) throw Error();
    const html = new DOMParser().parseFromString(await response.text(), 'text/html');
    if (html.body.dataset.portalReady !== 'true') throw Error();
    state.textContent = 'Nuevo corte disponible. ';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'cached-refresh-button';
    button.textContent = 'Mostrar datos actualizados';
    button.onclick = () => window.location.reload();
    state.appendChild(button);
  } catch (_) {
    state.textContent = 'No se pudo actualizar. Se conserva el último corte; vuelve a intentar al recargar.';
  }
})();
