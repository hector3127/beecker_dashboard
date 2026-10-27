// @ts-check
// Corte preparado: texto de la ultima consulta, boton «Actualizar datos» y
// espera de los bloques que aun no estan. Un corte nuevo se aplica recargando
// la pagina, una sola vez; los datos no se reemplazan solos.
import { apiGet, apiSend } from '#app/data/api-client.js';
import { finishLoading } from './metrics.js';

const POLL_MS = 5000;

/**
 * @param {object} options
 * @param {any} options.model Corte mostrado (revenue, costs, operations, commercial, loadedAt).
 * @param {Set<string>} options.loading Cifras que aun muestran «Cargando dato…».
 * @param {Record<string, string>} options.period Periodo de la URL para la API.
 */
export function mountCut({ model, loading, period }) {
  const control = /** @type {HTMLButtonElement | null} */ (document.getElementById('executive-prepare'));
  const status = document.getElementById('executive-cut-status');
  if (!control || !status) return;
  const { operations: ops } = model;
  const costs = model.costs || {};
  const coverage = costs.projects ? `${Math.max(0, costs.projects.length - Number(costs.pending || 0))} de ${costs.projects.length} proyectos con costos consultados` : '';
  status.textContent = model.loadedAt ? `Última consulta: ${new Date(model.loadedAt).toLocaleString('es-MX')}${coverage ? ` · ${coverage}` : ''}` : 'Consultando datos del periodo…';
  control.textContent = 'Actualizar datos';
  let ready = false;
  /** @type {ReturnType<typeof setInterval> | null} */
  let timer = null;
  let applyWhenReady = !model.loadedAt;
  const hasOperations = ops.projects !== null && ops.projects !== undefined;
  const missingBlocks = !model.loadedAt || !hasOperations || !model.commercial;
  const stop = () => {
    if (timer) clearInterval(timer);
    timer = null;
  };
  const fail = (/** @type {string} */ text) => {
    stop();
    applyWhenReady = false;
    finishLoading(loading);
    control.disabled = false;
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
        if (blocks.financial === false) {
          applyWhenReady = false;
          control.disabled = false;
          status.textContent = 'No se pudo completar la consulta financiera. Pulsa Actualizar datos para reintentar; no se mostrarán cifras inventadas.';
          return;
        }
        if (applyWhenReady) {
          applyWhenReady = false;
          status.textContent = 'Datos consultados. Mostrando el resultado…';
          location.reload();
          return;
        }
        ready = true;
        control.disabled = false;
        control.textContent = 'Ver corte preparado';
        status.textContent = data.partial ? 'Corte preparado con pendientes identificados. Pulsa para verlo.' : 'Nuevo corte preparado. Pulsa para verlo.';
      } else if (data.state === 'failed') fail('No se pudo completar. Se conserva el corte mostrado.');
      else if (data.state === 'running' || data.state === 'queued') status.textContent = 'Preparando en segundo plano. Se conserva el corte mostrado.';
    } catch (_) {
      fail('Sin conexión para actualizar. Se conserva el corte mostrado.');
    }
  }

  control.onclick = async () => {
    if (ready) {
      location.reload();
      return;
    }
    applyWhenReady = true;
    control.disabled = true;
    status.textContent = 'Consultando fuentes en segundo plano…';
    try {
      await apiSend('POST', `screens/executive/actualizar/${query(period)}`);
      await check();
      if (!ready && applyWhenReady) timer = setInterval(check, POLL_MS);
    } catch (_) {
      control.disabled = false;
      status.textContent = 'No se pudo iniciar la actualización.';
    }
  };
  if (missingBlocks) {
    timer = setInterval(check, POLL_MS);
    check();
  }
}

/** El periodo como cadena de consulta para el POST. @param {Record<string, string>} period */
function query(period) {
  const text = new URLSearchParams(period).toString();
  return text ? `?${text}` : '';
}
