// @ts-check
import { el } from '#app/lib/dom.js';
import { apiGet } from '#app/data/api-client.js';
import { workPlanDocuments } from './work_plan_model.js';

/** @type {Map<string, {documents?: any[], promise?: Promise<void>}>} */
const loads = new Map();

/** Mantiene los enlaces nuevos/eliminados al volver desde Cliente.
 * @param {string} id @param {any[]} documents */
export function updateWorkPlanDocuments(id, documents) {
  loads.set(id, { documents });
}

/** Vínculos de la ficha Cliente del mismo proyecto; sin abrir iframes externos.
 * @param {any} dashboard @param {'aer'|'ixs'} family */
export function workPlanLinks(dashboard, family) {
  const box = el('div', { class: family + '-actions', 'data-work-plan': '' });
  const id = String(dashboard.proyecto?.id || '');
  let error = '';
  const paint = () => {
    const links = workPlanDocuments(loads.get(id)?.documents || dashboard.cliente?.documentos || []);
    box.replaceChildren(...links.map(link => el('a', { href: link.url, target: '_blank', rel: 'noopener noreferrer',
      class: family + '-btn', text: 'Abrir ' + link.name })),
      el('small', { text: error || (links.length ? 'Vínculos registrados en Cliente.' : 'Registra tu plan en Cliente → Documentación, con tipo «Plan de trabajo» o «Roadmap».') }));
  };
  paint();
  // AER ya entrega Cliente en su dashboard; la API compartida es de IXS.
  if (family === 'aer') return box;
  if (id && !loads.has(id)) {
    /** @type {{documents?: any[], promise?: Promise<void>}} */
    const entry = {};
    loads.set(id, entry);
    entry.promise = apiGet(`screens/proyectos/${encodeURIComponent(id)}/cliente/`).then(({ data }) => {
      if (!data?.ok || String(data.proyectoId) !== id) throw new Error('Respuesta de proyecto inválida');
      // Una escritura en Cliente más reciente prevalece sobre esta lectura.
      if (loads.get(id) === entry) entry.documents = data.cliente?.documentos || [];
    }).catch(() => {
      error = 'No se pudieron consultar los vínculos. Reabre Planeación para reintentar.';
      if (loads.get(id) === entry) loads.delete(id);
    });
  }
  loads.get(id)?.promise?.then(() => { if (box.isConnected) paint(); });
  return box;
}
