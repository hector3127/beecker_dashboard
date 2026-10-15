// Conserva los datos y filtros visibles mientras prepara un nuevo corte.
(async function () {
  const state = document.getElementById('cached-page-state');
  if (!state) return;
  const url = new URL(window.location.href);
  url.searchParams.set('actualizar', '1');
  try {
    let partial = false;
    if (state.dataset?.refreshUrl) {
      const endpoint = new URL(state.dataset.refreshUrl, url);
      for (const key of ['periodo', 'anio', 'trimestre', 'mes', 'desde', 'hasta']) {
        if (url.searchParams.has(key)) endpoint.searchParams.set(key, url.searchParams.get(key));
      }
      const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      let response = await fetch(endpoint, {
        method: 'POST', credentials: 'same-origin',
        headers: {'X-CSRFToken': token || ''},
      });
      if (!response.ok) throw Error();
      let progress = await response.json();
      let attempts = 0;
      let stopped = false;
      window.addEventListener('pagehide', () => {stopped = true;}, {once: true});
      while (['queued', 'running'].includes(progress.state) && attempts < 120) {
        await new Promise(resolve => setTimeout(resolve, Math.min(2000 + attempts * 1000, 15000)));
        if (stopped) return;
        response = await fetch(endpoint, {credentials: 'same-origin', cache: 'no-store'});
        if (!response.ok) throw Error();
        progress = await response.json();
        attempts++;
      }
      if (progress.state !== 'ready') throw Error();
      partial = progress.partial;
    } else {
      const response = await fetch(url, {credentials: 'same-origin'});
      if (!response.ok) throw Error();
      const html = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (html.body.dataset.portalReady !== 'true') throw Error();
    }
    state.textContent = partial ? 'Nuevo corte parcial disponible. ' : 'Nuevo corte disponible. ';
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
