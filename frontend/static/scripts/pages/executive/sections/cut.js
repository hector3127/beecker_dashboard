// @ts-check
// Consulta el estado de preparación cuando faltan bloques del periodo.
import { apiGet } from '#app/data/api-client.js';
import { finishLoading } from './metrics.js';

const POLL_MS = 5000;

/**
 * @param {object} options
 * @param {any} options.model Corte mostrado (revenue, costs, operations, commercial, loadedAt).
 * @param {Set<string>} options.loading Cifras que aun muestran «Cargando dato…».
 * @param {Record<string, string>} options.period Periodo de la URL para la API.
 */
export function mountCut({ model, loading, period }) {
  const status = document.getElementById('executive-cut-status');
  if (!status) return;
  const { operations: ops } = model;
  status.textContent = model.loadedAt ? '' : 'Consultando datos del periodo…';
  /** @type {ReturnType<typeof setInterval> | null} */
  let timer = null;
  const hasOperations = ops.projects !== null && ops.projects !== undefined;
  const missingBlocks = !model.loadedAt || !hasOperations || !model.commercial;
  const stop = () => {
    if (timer) clearInterval(timer);
    timer = null;
  };
  const fail = (/** @type {string} */ text) => {
    stop();
    finishLoading(loading);
    status.textContent = text;
  };

  async function check() {
    try {
      const { data } = await apiGet('screens/executive/actualizar/', period, { cache: 'no-store' });
      const blocks = data.blocks || {};
      if ((!model.loadedAt && blocks.financial) || (!model.commercial && blocks.commercial) || (!hasOperations && blocks.operations)) {
        stop();
        location.reload();
        return;
      }
      if (data.state === 'ready') {
        stop();
        finishLoading(loading);
        status.textContent = blocks.financial === false
          ? 'No se pudo completar la consulta financiera. Consulta el periodo de nuevo para reintentar.'
          : data.partial ? 'Consulta terminada con datos pendientes.' : 'Consulta terminada.';
      } else if (data.state === 'idle' || data.state === 'busy') fail('La actualización no está en ejecución. Consulta el periodo de nuevo para reintentar.');
      else if (data.state === 'failed') fail('No se pudo completar. Se conserva el corte mostrado.');
      else if (data.state === 'running' || data.state === 'queued') status.textContent = 'Preparando en segundo plano. Se conserva el corte mostrado.';
    } catch (_) {
      fail('Sin conexión para actualizar. Se conserva el corte mostrado.');
    }
  }

  if (missingBlocks) {
    timer = setInterval(check, POLL_MS);
    check();
  }
}
