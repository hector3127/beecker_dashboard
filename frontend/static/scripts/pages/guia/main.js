// @ts-check
// Pantalla de ejemplo: une el cliente de datos con los estados de la interfaz.
import { apiGet } from '#app/data/api-client.js';
import { el } from '#app/lib/dom.js';
import { clearState, showError, showLoading } from '#app/ui/states.js';

const region = /** @type {HTMLElement} */ (document.getElementById('guia-api'));
let controller = new AbortController();

async function load() {
  controller.abort(); // una consulta nueva cancela la anterior
  controller = new AbortController();
  showLoading(region, 'Consultando la API…');
  try {
    const body = await apiGet('ping/', {}, { signal: controller.signal });
    clearState(region);
    region.append(
      el('p', { class: 'hs', text: `API disponible · ${body.meta.generated_at}` }),
      el('button', { type: 'button', class: 'btn btn-ghost', onclick: load, text: 'Probar de nuevo' }),
    );
  } catch (error) {
    if (controller.signal.aborted) return;
    showError(region, error, { onRetry: load });
  }
}

load();
