// @ts-check
import { apiGet, apiSend } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';

/** Keep source extraction separate from consulting an observed cut. */
export function mountExtraction() {
  const button = document.getElementById('eva-extract');
  const status = document.getElementById('eva-extraction-status');
  if (!button || !status) return;
  let busy = false;
  let timer;
  let waiting = false;
  let baseline;
  let requestedAt = 0;
  const render = (data) => {
    const issues = document.getElementById('eva-source-issues');
    if (issues) issues.replaceChildren(...(data.issues || []).map((issue) => el('li', { text: issue })));
    status.textContent = data.state === 'running'
      ? 'Extrayendo Azure y Clockify… Puedes seguir consultando el último corte.'
      : data.state === 'failed' ? 'La extracción falló. Se conserva el corte anterior.'
      : data.metrics?.total_seconds != null
        ? `Última extracción: ${data.metrics.total_seconds} s · Azure: ${data.metrics.azure_seconds ?? '—'} s · Clockify: ${data.metrics.clockify_seconds ?? '—'} s.`
        : 'Aún no hay una extracción guardada.';
    button.disabled = busy || data.state === 'running';
  };
  async function poll() {
    try {
      const { data } = await apiGet('screens/eva1/extraccion/', undefined, { cache: 'no-store' });
      render(data);
      if (data.state === 'failed' && requestedAt && data.id !== baseline) {
        busy = false;
        requestedAt = 0;
        render(data);
        return;
      }
      if (data.stale_job) {
        busy = false;
        status.textContent = 'La extracción quedó interrumpida. Vuelve a actualizar las fuentes.';
        button.disabled = false;
        return;
      }
      if (data.state === 'running') waiting = true;
      if ((waiting || requestedAt && data.id !== baseline) && data.state === 'ready') {
        location.reload();
        return;
      }
      if (requestedAt && data.state !== 'running' && data.id === baseline && Date.now() - requestedAt > 15000) {
        status.textContent = 'No se inició una nueva extracción. Vuelve a intentarlo.';
        busy = false;
        button.disabled = false;
        return;
      }
      if (data.state === 'running' || busy) timer = setTimeout(poll, 2500);
    } catch (error) {
      busy = false;
      button.disabled = false;
      status.textContent = error.message || 'No se pudo consultar la extracción.';
    }
  }
  button.addEventListener('click', async () => {
    if (busy) return;
    busy = true;
    button.disabled = true;
    clearTimeout(timer);
    try {
      const current = await apiGet('screens/eva1/extraccion/', undefined, { cache: 'no-store' });
      baseline = current.data.id;
      await apiSend('POST', 'screens/eva1/extraccion/', {});
      requestedAt = Date.now();
      status.textContent = 'Extracción solicitada. Consultando Azure y Clockify…';
      // A queued job may not have created its durable run yet.
      timer = setTimeout(poll, 2500);
    } catch (error) {
      busy = false;
      button.disabled = false;
      status.textContent = error.message || 'No se pudo iniciar la extracción.';
    }
  });
  window.addEventListener('pagehide', () => clearTimeout(timer), { once: true });
  poll();
}
