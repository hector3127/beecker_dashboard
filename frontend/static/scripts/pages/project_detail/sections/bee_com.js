// @ts-check
// Centro de Comunicación de IXB/SaaS/RaaS: lee y publica por API v1, filtra y
// abre el detalle y el formulario. Los comunicados son del portafolio; aquí se
// ven los del proyecto abierto y los generales.
import { payloadOf } from "./bee_com_model.js";
import { detailModal, editModal, paintList, paintLoading } from "./bee_com_view.js";

/** @param {{communications: () => Promise<any>, saveCommunication: (payload: any) => Promise<any>}} api */
export function createCommunicationController(api) {
  const state = { items: /** @type {any[]} */ ([]), tipo: "Todos", proyecto: "", contextProject: "", orden: "recientes", busqueda: "", error: "", loading: false };
  /** @type {HTMLElement | null} */
  let root = null;
  /** @type {any} */
  let data = null;
  /** @type {any} */
  let guards = null;
  let request = 0;

  const live = () => !!root && root.isConnected && guards.current(data) && guards.active();
  const closeModal = () => document.getElementById("bee-com-modal")?.remove();
  const paint = () => root && paintList(root, state, handlers);
  const find = (/** @type {string} */ uid) => state.items.find((i) => i.uid === uid);

  const handlers = {
    filter(/** @type {string} */ key, /** @type {string} */ value) {
      /** @type {any} */ (state)[key] = value;
      paint();
    },
    open(/** @type {string} */ uid) {
      const item = find(uid);
      if (!item) return;
      closeModal();
      document.body.append(detailModal(item, { close: closeModal, edit: handlers.edit }));
    },
    edit(/** @type {string} */ uid = "") {
      const item = find(uid) || {};
      closeModal();
      document.body.append(editModal(item, state, { close: closeModal, save }, uid));
    },
  };

  /** @param {Event} event @param {string} uid */
  async function save(event, uid) {
    event.preventDefault();
    const form = /** @type {HTMLFormElement} */ (event.target);
    const button = /** @type {HTMLButtonElement} */ (form.querySelector("[type=submit]"));
    const failure = (/** @type {string} */ message) => {
      button.disabled = false;
      button.textContent = "Publicar comunicado";
      const box = document.getElementById("bee-com-error");
      if (box) box.textContent = message;
    };
    button.disabled = true;
    button.textContent = "Guardando…";
    try {
      const result = await api.saveCommunication(payloadOf(new FormData(form), uid, /** @type {HTMLInputElement} */ (form.elements.namedItem("importante")).checked));
      if (!result || !result.ok) return failure((result && result.error) || "No se pudo guardar.");
      button.disabled = false;
      button.textContent = "Publicar comunicado";
      state.items = result.comunicados || [];
      closeModal();
      if (live()) paint();
    } catch (error) {
      failure((error instanceof Error && error.message) || String(error));
    }
  }

  async function load() {
    if (!root) return;
    const mine = ++request;
    state.loading = true;
    paintLoading(root);
    try {
      const result = await api.communications();
      if (mine !== request || !live()) return;
      state.loading = false;
      state.error = result && result.ok ? "" : (result && result.error) || "No se pudieron cargar los comunicados.";
      state.items = result && result.ok ? result.comunicados || [] : [];
    } catch (error) {
      if (mine !== request || !live()) return;
      state.loading = false;
      state.error = (error instanceof Error && error.message) || String(error);
      state.items = [];
    }
    paint();
  }

  return {
    /** @param {HTMLElement} target @param {any} project @param {{current: (p: any) => boolean, active: () => boolean}} lifecycle */
    mount(target, project, lifecycle) {
      closeModal();
      data = project;
      guards = lifecycle;
      Object.assign(state, { contextProject: String(project.proyecto.id || ""), proyecto: "", tipo: "Todos", busqueda: "" });
      root = document.createElement("div");
      root.id = "bee-com-root";
      target.replaceChildren(root);
      load();
    },
  };
}
